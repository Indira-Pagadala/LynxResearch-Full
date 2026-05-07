# app/models/citation.py

import uuid
from sqlalchemy import Text, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class Citation(Base):
    __tablename__ = "citations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research_runs.id", ondelete="CASCADE")
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scraped_documents.id", ondelete="CASCADE")
    )
    citation_key: Mapped[str] = mapped_column(
        String(100), nullable=False   # e.g. "Smith2023" or "WHO2024"
    )
    apa_string: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    run: Mapped["ResearchRun"] = relationship("ResearchRun", back_populates="citations")
    document: Mapped["ScrapedDocument"] = relationship(
        "ScrapedDocument", back_populates="citations"
    )

    def __repr__(self) -> str:
        return f"<Citation key={self.citation_key!r}>"