# app/models/chat_message.py

import uuid
from datetime import datetime
from sqlalchemy import Text, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("research_runs.id", ondelete="CASCADE")
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False  # 'user' or 'assistant'
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    # Relationships
    run: Mapped["ResearchRun"] = relationship("ResearchRun", backref="chat_messages")

    def __repr__(self) -> str:
        return f"<ChatMessage id={self.id} run_id={self.run_id} role={self.role}>"
