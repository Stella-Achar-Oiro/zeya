import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.conversation import MessageDirection


class ConversationCreate(BaseModel):
    user_id: uuid.UUID
    message_direction: MessageDirection
    message_text: str
    gestational_age_at_message: Optional[int] = None
    danger_sign_detected: bool = False
    danger_sign_keywords: Optional[str] = None
    response_time_ms: Optional[int] = None
    ai_model_used: Optional[str] = None


class ConversationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    message_direction: MessageDirection
    message_text: str
    gestational_age_at_message: Optional[int]
    danger_sign_detected: bool
    danger_sign_keywords: Optional[str]
    response_time_ms: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationListResponse(BaseModel):
    conversations: list[ConversationResponse]
    total: int
