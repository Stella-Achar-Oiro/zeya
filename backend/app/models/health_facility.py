"""Health facility model for emergency referrals."""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Float, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FacilityType(str, enum.Enum):
    """Types of health facilities."""

    HOSPITAL = "hospital"
    HEALTH_CENTER = "health_center"
    DISPENSARY = "dispensary"
    CLINIC = "clinic"
    MATERNITY_HOME = "maternity_home"


class FacilityLevel(str, enum.Enum):
    """Level of care provided."""

    LEVEL_1 = "level_1"  # Dispensary
    LEVEL_2 = "level_2"  # Health center
    LEVEL_3 = "level_3"  # Sub-county hospital
    LEVEL_4 = "level_4"  # County referral hospital
    LEVEL_5 = "level_5"  # National referral hospital
    LEVEL_6 = "level_6"  # National teaching/research hospital


class HealthFacility(Base):
    """Health facility for emergency referrals and contact information."""

    __tablename__ = "health_facilities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    facility_type: Mapped[FacilityType] = mapped_column(
        Enum(FacilityType, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    facility_level: Mapped[FacilityLevel] = mapped_column(
        Enum(FacilityLevel, values_callable=lambda x: [e.value for e in x]),
        nullable=True
    )

    # Contact information
    phone_number: Mapped[str] = mapped_column(String(50), nullable=True)
    emergency_line: Mapped[str] = mapped_column(String(50), nullable=True)
    email: Mapped[str] = mapped_column(String(100), nullable=True)

    # Location
    county: Mapped[str] = mapped_column(String(100), nullable=False)
    sub_county: Mapped[str] = mapped_column(String(100), nullable=True)
    ward: Mapped[str] = mapped_column(String(100), nullable=True)
    physical_address: Mapped[str] = mapped_column(Text, nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=True)
    longitude: Mapped[float] = mapped_column(Float, nullable=True)

    # Services
    has_maternity_services: Mapped[bool] = mapped_column(Boolean, default=True)
    has_emergency_services: Mapped[bool] = mapped_column(Boolean, default=True)
    has_24h_services: Mapped[bool] = mapped_column(Boolean, default=False)
    has_ambulance: Mapped[bool] = mapped_column(Boolean, default=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    display_priority: Mapped[int] = mapped_column(
        default=100, nullable=False
    )  # Lower number = higher priority

    # Additional info
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    website_url: Mapped[str] = mapped_column(String(200), nullable=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<HealthFacility {self.name} ({self.county})>"

    def format_for_emergency_response(self, include_details: bool = False) -> str:
        """Format facility information for emergency response message."""
        parts = [f"- {self.name}"]

        if self.phone_number:
            parts.append(f": {self.phone_number}")
        elif self.emergency_line:
            parts.append(f": {self.emergency_line}")

        if include_details:
            details = []
            if self.physical_address:
                details.append(self.physical_address)
            if self.has_24h_services:
                details.append("24-hour services")
            if self.has_ambulance:
                details.append("Ambulance available")

            if details:
                parts.append(f" ({', '.join(details)})")

        return "".join(parts)
