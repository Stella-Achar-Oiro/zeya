import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr

from app.models.admin import AdminRole


class AdminCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: str
    role: AdminRole = AdminRole.RESEARCHER


class AdminLogin(BaseModel):
    username: str
    password: str


class AdminResponse(BaseModel):
    id: uuid.UUID
    email: str
    username: str
    full_name: str
    role: AdminRole
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class DashboardOverview(BaseModel):
    total_users: int
    intervention_users: int
    control_users: int
    active_users_7d: int
    total_conversations_7d: int
    danger_sign_alerts_pending: int
    avg_response_time_ms: Optional[float]


class EngagementTrend(BaseModel):
    week: int
    total_messages: int
    active_users: int
    avg_response_time: Optional[float]


class TopicCount(BaseModel):
    topic: str
    count: int


class DangerSignAlert(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    phone_number: str
    message_text: str
    danger_sign_keywords: Optional[str]
    gestational_age: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}
