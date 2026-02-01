"""
Conversation viewing endpoints for the admin dashboard.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_admin
from app.core.database import get_db
from app.models.admin import AdminUser
from app.models.conversation import Conversation
from app.schemas.conversation import ConversationListResponse, ConversationResponse

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    user_id: Optional[uuid.UUID] = None,
    danger_signs_only: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> ConversationListResponse:
    """List conversations with optional filters."""
    query = select(Conversation)
    count_query = select(func.count(Conversation.id))

    if user_id:
        query = query.where(Conversation.user_id == user_id)
        count_query = count_query.where(Conversation.user_id == user_id)
    if danger_signs_only:
        query = query.where(Conversation.danger_sign_detected.is_(True))
        count_query = count_query.where(Conversation.danger_sign_detected.is_(True))

    query = query.order_by(Conversation.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    conversations = [
        ConversationResponse.model_validate(c) for c in result.scalars().all()
    ]

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return ConversationListResponse(conversations=conversations, total=total)
