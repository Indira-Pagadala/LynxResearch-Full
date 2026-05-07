# app/api/workspaces.py

import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.workspace import Workspace
from app.models.run import ResearchRun
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


class CreateWorkspaceRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    user_id: str = Field(..., min_length=1)


class WorkspaceResponse(BaseModel):
    id: uuid.UUID
    name: str
    user_id: str
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/", response_model=WorkspaceResponse, status_code=201)
async def create_workspace(
    request: CreateWorkspaceRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new workspace for a user."""
    workspace = Workspace(
        name=request.name,
        user_id=request.user_id,
    )
    db.add(workspace)
    await db.flush()
    await db.refresh(workspace)
    logger.info(f"✅ Workspace created: {workspace.name} for user {request.user_id}")
    return workspace


@router.get("/", response_model=list[WorkspaceResponse])
async def list_workspaces(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List all workspaces for a user."""
    result = await db.execute(
        select(Workspace)
        .where(Workspace.user_id == user_id)
        .order_by(Workspace.created_at.asc())
    )
    return result.scalars().all()


@router.delete("/{workspace_id}", status_code=204)
async def delete_workspace(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a workspace. Runs in it will have workspace_id set to NULL."""
    workspace = await db.get(Workspace, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    await db.delete(workspace)
    await db.flush()
    logger.info(f"🗑️ Workspace deleted: {workspace.name}")
