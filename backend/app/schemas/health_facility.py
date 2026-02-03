"""Pydantic schemas for health facility management."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl

from app.models.health_facility import FacilityLevel, FacilityType


class HealthFacilityBase(BaseModel):
    """Base schema for health facility."""

    name: str = Field(..., min_length=1, max_length=200)
    facility_type: FacilityType
    facility_level: Optional[FacilityLevel] = None

    # Contact information
    phone_number: Optional[str] = Field(None, max_length=50)
    emergency_line: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=100)

    # Location
    county: str = Field(..., min_length=1, max_length=100)
    sub_county: Optional[str] = Field(None, max_length=100)
    ward: Optional[str] = Field(None, max_length=100)
    physical_address: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)

    # Services
    has_maternity_services: bool = True
    has_emergency_services: bool = True
    has_24h_services: bool = False
    has_ambulance: bool = False

    # Status
    is_active: bool = True
    is_verified: bool = False
    display_priority: int = Field(default=100, ge=1, le=1000)

    # Additional info
    notes: Optional[str] = None
    website_url: Optional[str] = Field(None, max_length=200)


class HealthFacilityCreate(HealthFacilityBase):
    """Schema for creating a new health facility."""

    pass


class HealthFacilityUpdate(BaseModel):
    """Schema for updating a health facility."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    facility_type: Optional[FacilityType] = None
    facility_level: Optional[FacilityLevel] = None

    # Contact information
    phone_number: Optional[str] = Field(None, max_length=50)
    emergency_line: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=100)

    # Location
    county: Optional[str] = Field(None, min_length=1, max_length=100)
    sub_county: Optional[str] = Field(None, max_length=100)
    ward: Optional[str] = Field(None, max_length=100)
    physical_address: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)

    # Services
    has_maternity_services: Optional[bool] = None
    has_emergency_services: Optional[bool] = None
    has_24h_services: Optional[bool] = None
    has_ambulance: Optional[bool] = None

    # Status
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    display_priority: Optional[int] = Field(None, ge=1, le=1000)

    # Additional info
    notes: Optional[str] = None
    website_url: Optional[str] = Field(None, max_length=200)


class HealthFacilityResponse(HealthFacilityBase):
    """Schema for health facility response."""

    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HealthFacilityList(BaseModel):
    """Schema for paginated list of health facilities."""

    total: int
    facilities: list[HealthFacilityResponse]
    page: int
    page_size: int


class EmergencyContactsResponse(BaseModel):
    """Schema for emergency contacts response."""

    county: str
    facilities: list[HealthFacilityResponse]
    message_text_en: str
    message_text_sw: str
