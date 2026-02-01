"""
Authentication endpoints for the admin dashboard.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.admin import AdminUser
from app.schemas.admin import AdminCreate, AdminLogin, AdminResponse, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: AdminLogin,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate admin user and return JWT token."""
    result = await db.execute(
        select(AdminUser).where(AdminUser.username == credentials.username)
    )
    admin = result.scalar_one_or_none()

    if admin is None or not verify_password(credentials.password, admin.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    token = create_access_token(data={"sub": admin.username, "role": admin.role.value})
    return TokenResponse(access_token=token)


@router.post("/register", response_model=AdminResponse, status_code=status.HTTP_201_CREATED)
async def register_admin(
    admin_data: AdminCreate,
    db: AsyncSession = Depends(get_db),
) -> AdminUser:
    """Register a new admin user. Should be restricted in production."""
    # Check for existing user
    existing = await db.execute(
        select(AdminUser).where(
            (AdminUser.username == admin_data.username)
            | (AdminUser.email == admin_data.email)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already exists",
        )

    admin = AdminUser(
        email=admin_data.email,
        username=admin_data.username,
        hashed_password=get_password_hash(admin_data.password),
        full_name=admin_data.full_name,
        role=admin_data.role,
    )
    db.add(admin)
    await db.flush()
    return admin
