import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.assessment import AssessmentType


class AssessmentCreate(BaseModel):
    user_id: uuid.UUID
    assessment_type: AssessmentType
    total_score: int
    max_score: int = 100
    responses: Optional[dict] = None


class AssessmentResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    assessment_type: AssessmentType
    total_score: int
    max_score: int
    responses: Optional[dict]
    completed_at: datetime

    model_config = {"from_attributes": True}
