# app/api/chat.py

import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.database import get_db
from app.models.report import Report
from app.models.run import ResearchRun
from app.models.chat_message import ChatMessage
from app.schemas.report import (
    ChatRequest, ChatResponse,
    ChatMessageResponse, ChatThreadResponse,
)
from app.services.rag_service import chat_with_report

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["RAG Chat"])


@router.get("/threads", response_model=list[ChatThreadResponse])
async def list_chat_threads(
    workspace_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """List all runs that have chat messages (i.e. active chat threads)."""
    # Subquery: runs with at least one chat message
    stmt = (
        select(
            ChatMessage.run_id,
            func.count(ChatMessage.id).label("message_count"),
            func.max(ChatMessage.created_at).label("updated_at"),
        )
        .group_by(ChatMessage.run_id)
        .subquery()
    )

    query = (
        select(
            ResearchRun.id,
            ResearchRun.topic,
            stmt.c.message_count,
            stmt.c.updated_at,
        )
        .join(stmt, ResearchRun.id == stmt.c.run_id)
    )
    if workspace_id is not None:
        query = query.where(ResearchRun.workspace_id == workspace_id)
    result = await db.execute(query.order_by(desc(stmt.c.updated_at)))

    threads = []
    for row in result.all():
        # Get last message content
        last_msg_result = await db.execute(
            select(ChatMessage.content)
            .where(ChatMessage.run_id == row[0])
            .order_by(desc(ChatMessage.created_at))
            .limit(1)
        )
        last_msg = last_msg_result.scalar_one_or_none() or ""

        threads.append(ChatThreadResponse(
            run_id=row[0],
            topic=row[1],
            message_count=row[2],
            updated_at=row[3],
            last_message=last_msg,
        ))

    return threads


@router.get("/{run_id}/history", response_model=list[ChatMessageResponse])
async def get_chat_history(
    run_id: uuid.UUID,
    workspace_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Get all chat messages for a run, ordered chronologically."""
    run = await db.get(ResearchRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Research run not found")
    if workspace_id is not None and run.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Research run not found")

    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.run_id == run_id)
        .order_by(ChatMessage.created_at.asc())
    )
    return result.scalars().all()


@router.post("/{run_id}", response_model=ChatResponse)
async def chat_with_run_report(
    run_id: uuid.UUID,
    request: ChatRequest,
    workspace_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Chat with the generated research report using RAG.
    Requires the run to be in 'done' status.
    Persists both user question and assistant answer.
    """
    # Verify run exists and is done
    run = await db.get(ResearchRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Research run not found")
    if workspace_id is not None and run.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Research run not found")
    if run.status != "done":
        raise HTTPException(
            status_code=400,
            detail=f"Run is not complete yet. Current status: {run.status}"
        )

    # Verify report exists
    result = await db.execute(select(Report).where(Report.run_id == run_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Save user message
    user_msg = ChatMessage(
        run_id=run_id,
        role="user",
        content=request.question,
    )
    db.add(user_msg)

    # Generate RAG answer — pass report markdown as fallback context
    answer = await chat_with_report(
        run_id=str(run_id),
        question=request.question,
        conversation_history=request.conversation_history,
        report_markdown=report.markdown_content or "",
    )

    # Save assistant message
    assistant_msg = ChatMessage(
        run_id=run_id,
        role="assistant",
        content=answer,
    )
    db.add(assistant_msg)
    await db.flush()

    return ChatResponse(answer=answer, run_id=str(run_id))