"""
User management endpoints for the admin dashboard.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_admin, require_role
from app.core.database import get_db
from app.models.admin import AdminRole, AdminUser
from app.models.user import StudyGroup
from app.schemas.user import UserListResponse, UserResponse, UserUpdate
from app.services.user_service import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    study_group: Optional[StudyGroup] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> UserListResponse:
    """List all users with pagination and filters."""
    users, total = await user_service.list_users(
        db, page=page, page_size=page_size, study_group=study_group, is_active=is_active
    )

    user_responses = []
    for u in users:
        resp = UserResponse.model_validate(u)
        resp.current_gestational_age = u.current_gestational_age()
        user_responses.append(resp)

    return UserListResponse(
        users=user_responses,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> UserResponse:
    """Get a specific user's profile."""
    user = await user_service.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    resp = UserResponse.model_validate(user)
    resp.current_gestational_age = user.current_gestational_age()
    return resp


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    update_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_role(AdminRole.ADMIN)),
) -> UserResponse:
    """Update a user's profile. Admin only."""
    user = await user_service.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    updated = await user_service.update_user(db, user, update_data)
    resp = UserResponse.model_validate(updated)
    resp.current_gestational_age = updated.current_gestational_age()
    return resp


@router.post("/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_role(AdminRole.ADMIN)),
) -> UserResponse:
    """Deactivate a user. Admin only."""
    user = await user_service.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    deactivated = await user_service.deactivate_user(db, user)
    return UserResponse.model_validate(deactivated)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_data(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_role(AdminRole.ADMIN)),
) -> None:
    """Delete a user and all their data. GDPR/Kenya DPA compliance."""
    user = await user_service.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await db.delete(user)
