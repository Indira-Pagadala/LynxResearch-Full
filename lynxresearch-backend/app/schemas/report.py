# app/schemas/report.py

from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid


class ReportResponse(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    word_count: Optional[int] = None
    page_count: Optional[int] = None
    pdf_path: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    question: str
    conversation_history: list[dict] = []


class ChatResponse(BaseModel):
    answer: str
    run_id: str


class ChatMessageResponse(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatThreadResponse(BaseModel):
    run_id: uuid.UUID
    topic: str
    last_message: str
    message_count: int
    updated_at: datetime


class DocumentResponse(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    url: str
    title: Optional[str] = None
    source_type: str
    relevance_score: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True