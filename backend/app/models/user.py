import enum
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Enum, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class StudyGroup(str, enum.Enum):
    INTERVENTION = "intervention"
    CONTROL = "control"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    phone_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    whatsapp_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=True)
    study_group: Mapped[StudyGroup] = mapped_column(
        Enum(StudyGroup), default=StudyGroup.INTERVENTION, nullable=False
    )
    gestational_age_at_enrollment: Mapped[int] = mapped_column(
        Integer, nullable=True
    )
    expected_delivery_date: Mapped[date] = mapped_column(Date, nullable=True)
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    language_preference: Mapped[str] = mapped_column(
        String(10), default="en", nullable=False
    )
    registration_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_given_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    conversations = relationship("Conversation", back_populates="user", lazy="selectin")
    assessments = relationship("KnowledgeAssessment", back_populates="user", lazy="selectin")
    engagement_metrics = relationship("EngagementMetric", back_populates="user", lazy="selectin")

    def current_gestational_age(self) -> int | None:
        """Calculate current gestational age based on enrollment data."""
        if self.gestational_age_at_enrollment is None:
            return None
        weeks_since_enrollment = (
            datetime.now(timezone.utc) - self.enrolled_at
        ).days // 7
        return self.gestational_age_at_enrollment + weeks_since_enrollment
