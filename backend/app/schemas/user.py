import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from app.models.user import StudyGroup


class UserCreate(BaseModel):
    phone_number: str
    whatsapp_id: str
    name: Optional[str] = None
    study_group: StudyGroup = StudyGroup.INTERVENTION
    gestational_age_at_enrollment: Optional[int] = None
    expected_delivery_date: Optional[date] = None
    language_preference: str = "en"

    model_config = {"use_enum_values": True}


class UserUpdate(BaseModel):
    name: Optional[str] = None
    gestational_age_at_enrollment: Optional[int] = None
    expected_delivery_date: Optional[date] = None
    is_active: Optional[bool] = None
    language_preference: Optional[str] = None
    registration_complete: Optional[bool] = None
    consent_given: Optional[bool] = None


class UserResponse(BaseModel):
    id: uuid.UUID
    phone_number: str
    whatsapp_id: str
    name: Optional[str]
    study_group: StudyGroup
    gestational_age_at_enrollment: Optional[int]
    expected_delivery_date: Optional[date]
    enrolled_at: datetime
    is_active: bool
    language_preference: str
    registration_complete: bool
    consent_given: bool
    current_gestational_age: Optional[int] = None

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    users: list[UserResponse]
    total: int
    page: int
    page_size: int
