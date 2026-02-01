import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MessageDirection(str, enum.Enum):
    INCOMING = "incoming"
    OUTGOING = "outgoing"


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    message_direction: Mapped[MessageDirection] = mapped_column(
        Enum(MessageDirection), nullable=False
    )
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    gestational_age_at_message: Mapped[int] = mapped_column(Integer, nullable=True)
    danger_sign_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    danger_sign_keywords: Mapped[str] = mapped_column(Text, nullable=True)
    response_time_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    ai_model_used: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user = relationship("User", back_populates="conversations")
