# app/schemas/run.py

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
import uuid


REPORT_STYLES = Literal[
    "business",    # Market analysis, revenue, investment, competitive landscape
    "academic",    # Literature review, methodology, citations, formal analysis  
    "medical",     # Clinical focus, symptoms, treatments, patient outcomes, research
    "technical",   # Engineering, architecture, specs, implementation details
    "general",     # Balanced overview accessible to a general audience
    "policy",      # Regulatory, government, public policy angle
]


class CreateRunRequest(BaseModel):
    topic: str = Field(
        ..., min_length=5, max_length=500,
        description="Enter the topic"
    )
    report_style: REPORT_STYLES = Field(
        default="general",
        description="Select the style of the research report"
    )
    workspace_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Optional workspace to associate this run with"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "topic": "PCOS and its effects on young women",
                "report_style": "medical",
            }
        }


class RunStatusResponse(BaseModel):
    id: uuid.UUID
    topic: str
    status: str
    progress: int
    current_stage: Optional[str] = None
    error_message: Optional[str] = None
    workspace_id: Optional[uuid.UUID] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RunListItem(BaseModel):
    id: uuid.UUID
    topic: str
    report_style: str
    status: str
    progress: int
    current_stage: Optional[str] = None
    workspace_id: Optional[uuid.UUID] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True