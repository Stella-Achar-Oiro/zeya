import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class EngagementMetric(Base):
    __tablename__ = "engagement_metrics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    week_number: Mapped[int] = mapped_column(Integer, nullable=False)
    messages_sent: Mapped[int] = mapped_column(Integer, default=0)
    messages_received: Mapped[int] = mapped_column(Integer, default=0)
    avg_response_time_seconds: Mapped[float] = mapped_column(Float, nullable=True)
    active_days: Mapped[int] = mapped_column(Integer, default=0)
    topics_discussed: Mapped[int] = mapped_column(Integer, default=0)
    danger_signs_flagged: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user = relationship("User", back_populates="engagement_metrics")
