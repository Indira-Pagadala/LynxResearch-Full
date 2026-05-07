# app/models/run.py

import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class ResearchRun(Base):
    __tablename__ = "research_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    report_style: Mapped[str] = mapped_column(
        String(50), default="general", nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )
    progress: Mapped[int] = mapped_column(Integer, default=0)
    current_stage: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    documents: Mapped[list["ScrapedDocument"]] = relationship(
        "ScrapedDocument", back_populates="run", cascade="all, delete-orphan"
    )
    chunks: Mapped[list["TextChunk"]] = relationship(
        "TextChunk", back_populates="run", cascade="all, delete-orphan"
    )
    citations: Mapped[list["Citation"]] = relationship(
        "Citation", back_populates="run", cascade="all, delete-orphan"
    )
    report: Mapped["Report | None"] = relationship(
        "Report", back_populates="run", cascade="all, delete-orphan",
        uselist=False
    )
    workspace: Mapped["Workspace | None"] = relationship(
        "Workspace", back_populates="runs"
    )

    def __repr__(self) -> str:
        return f"<ResearchRun id={self.id} topic={self.topic!r} style={self.report_style}>"