# app/models/document.py

import uuid
from datetime import datetime, date
from sqlalchemy import String, Text, Float, Date, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class ScrapedDocument(Base):
    __tablename__ = "scraped_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research_runs.id", ondelete="CASCADE")
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    publication_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_type: Mapped[str] = mapped_column(
        String(20), default="html"   # 'html' | 'pdf'
    )
    relevance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    # Relationships
    run: Mapped["ResearchRun"] = relationship("ResearchRun", back_populates="documents")
    chunks: Mapped[list["TextChunk"]] = relationship(
        "TextChunk", back_populates="document", cascade="all, delete-orphan"
    )
    citations: Mapped[list["Citation"]] = relationship(
        "Citation", back_populates="document"
    )

    def __repr__(self) -> str:
        return f"<ScrapedDocument id={self.id} url={self.url!r}>"