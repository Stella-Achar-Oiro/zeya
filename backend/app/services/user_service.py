"""
User management service.

Handles user registration, profile management, and gestational age tracking.
"""

import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import StudyGroup, User
from app.schemas.user import UserCreate, UserUpdate

logger = logging.getLogger(__name__)


class UserService:
    """Service for user CRUD operations and business logic."""

    @staticmethod
    async def get_by_whatsapp_id(
        db: AsyncSession, whatsapp_id: str
    ) -> Optional[User]:
        """Find a user by their WhatsApp ID."""
        result = await db.execute(
            select(User).where(User.whatsapp_id == whatsapp_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
        """Find a user by their UUID."""
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def create_user(db: AsyncSession, user_data: UserCreate) -> User:
        """Create a new user."""
        data = user_data.model_dump()
        # Explicitly convert enum to its value
        if 'study_group' in data:
            if isinstance(data['study_group'], StudyGroup):
                data['study_group'] = data['study_group'].value
            elif isinstance(data['study_group'], str):
                # Handle case where Pydantic already converted to string enum name
                data['study_group'] = data['study_group'].lower()
        user = User(**data)
        db.add(user)
        await db.flush()
        return user

    @staticmethod
    async def update_user(
        db: AsyncSession, user: User, update_data: UserUpdate
    ) -> User:
        """Update user fields."""
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(user, field, value)
        if "consent_given" in update_dict and update_dict["consent_given"]:
            user.consent_given_at = datetime.now(timezone.utc)
        await db.flush()
        return user

    @staticmethod
    async def set_gestational_age(
        db: AsyncSession, user: User, weeks: int
    ) -> User:
        """Set gestational age and calculate expected delivery date."""
        user.gestational_age_at_enrollment = weeks
        remaining_weeks = 40 - weeks
        user.expected_delivery_date = (
            date.today() + timedelta(weeks=remaining_weeks)
        )
        await db.flush()
        return user

    @staticmethod
    async def list_users(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        study_group: Optional[StudyGroup] = None,
        is_active: Optional[bool] = None,
    ) -> tuple[list[User], int]:
        """List users with pagination and optional filters."""
        query = select(User)
        count_query = select(func.count(User.id))

        if study_group is not None:
            query = query.where(User.study_group == study_group)
            count_query = count_query.where(User.study_group == study_group)
        if is_active is not None:
            query = query.where(User.is_active == is_active)
            count_query = count_query.where(User.is_active == is_active)

        query = query.order_by(User.enrolled_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        users = list(result.scalars().all())

        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        return users, total

    @staticmethod
    async def get_active_users_count(db: AsyncSession, days: int = 7) -> int:
        """Count users who have been active in the last N days."""
        from app.models.conversation import Conversation

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        result = await db.execute(
            select(func.count(func.distinct(Conversation.user_id))).where(
                Conversation.created_at >= cutoff
            )
        )
        return result.scalar() or 0

    @staticmethod
    async def deactivate_user(db: AsyncSession, user: User) -> User:
        """Deactivate a user."""
        user.is_active = False
        await db.flush()
        return user


user_service = UserService()
