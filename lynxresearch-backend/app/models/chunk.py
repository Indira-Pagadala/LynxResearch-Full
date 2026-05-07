# app/models/chunk.py

import uuid
from sqlalchemy import Text, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class TextChunk(Base):
    __tablename__ = "text_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scraped_documents.id", ondelete="CASCADE")
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research_runs.id", ondelete="CASCADE")
    )
    chunk_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    qdrant_point_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    document: Mapped["ScrapedDocument"] = relationship(
        "ScrapedDocument", back_populates="chunks"
    )
    run: Mapped["ResearchRun"] = relationship("ResearchRun", back_populates="chunks")

    def __repr__(self) -> str:
        return f"<TextChunk id={self.id} index={self.chunk_index}>"