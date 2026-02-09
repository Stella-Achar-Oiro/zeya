"""API endpoints for health facility management."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_admin
from app.core.database import get_db
from app.models.admin import AdminUser
from app.schemas.health_facility import (
    EmergencyContactsResponse,
    HealthFacilityCreate,
    HealthFacilityList,
    HealthFacilityResponse,
    HealthFacilityUpdate,
)
from app.services.health_facility_service import health_facility_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health-facilities", tags=["health-facilities"])


@router.get("", response_model=HealthFacilityList)
async def list_facilities(
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    county: Optional[str] = None,
    active_only: bool = Query(True),
    _admin: AdminUser = Depends(get_current_admin),
) -> HealthFacilityList:
    """
    List all health facilities with pagination.

    Requires admin authentication.
    """
    facilities, total = await health_facility_service.get_all(
        db, skip=skip, limit=limit, county=county, active_only=active_only
    )

    return HealthFacilityList(
        total=total,
        facilities=[HealthFacilityResponse.model_validate(f) for f in facilities],
        page=skip // limit + 1,
        page_size=limit,
    )


@router.get("/emergency/{county}", response_model=EmergencyContactsResponse)
async def get_emergency_contacts(
    county: str,
    db: AsyncSession = Depends(get_db),
    language: str = Query("en", regex="^(en|sw)$"),
    _admin: AdminUser = Depends(get_current_admin),
) -> EmergencyContactsResponse:
    """
    Get emergency contact information for a specific county.

    Returns the top emergency facilities and formatted messages in both languages.
    Requires admin authentication.
    """
    facilities = await health_facility_service.get_emergency_facilities(
        db, county=county, limit=5
    )

    if not facilities:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No emergency facilities found for county: {county}",
        )

    message_en = health_facility_service.format_emergency_message(
        facilities, language="en"
    )
    message_sw = health_facility_service.format_emergency_message(
        facilities, language="sw"
    )

    return EmergencyContactsResponse(
        county=county,
        facilities=[HealthFacilityResponse.model_validate(f) for f in facilities],
        message_text_en=message_en,
        message_text_sw=message_sw,
    )


@router.get("/{facility_id}", response_model=HealthFacilityResponse)
async def get_facility(
    facility_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
) -> HealthFacilityResponse:
    """
    Get a specific health facility by ID.

    Requires admin authentication.
    """
    facility = await health_facility_service.get_by_id(db, facility_id)

    if not facility:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Health facility not found"
        )

    return HealthFacilityResponse.model_validate(facility)


@router.post("", response_model=HealthFacilityResponse, status_code=status.HTTP_201_CREATED)
async def create_facility(
    facility_data: HealthFacilityCreate,
    db: AsyncSession = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
) -> HealthFacilityResponse:
    """
    Create a new health facility.

    Requires admin authentication.
    """
    facility = await health_facility_service.create(db, facility_data)
    await db.commit()

    logger.info("Health facility created: %s by admin %s", facility.id, _admin.username)
    return HealthFacilityResponse.model_validate(facility)


@router.patch("/{facility_id}", response_model=HealthFacilityResponse)
async def update_facility(
    facility_id: UUID,
    facility_data: HealthFacilityUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
) -> HealthFacilityResponse:
    """
    Update a health facility.

    Requires admin authentication.
    """
    facility = await health_facility_service.get_by_id(db, facility_id)

    if not facility:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Health facility not found"
        )

    facility = await health_facility_service.update(db, facility, facility_data)
    await db.commit()

    logger.info("Health facility updated: %s by admin %s", facility.id, _admin.username)
    return HealthFacilityResponse.model_validate(facility)


@router.delete("/{facility_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_facility(
    facility_id: UUID,
    hard_delete: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
) -> None:
    """
    Delete a health facility.

    By default, performs a soft delete (marks as inactive).
    Set hard_delete=true to permanently delete the record.

    Requires admin authentication.
    """
    facility = await health_facility_service.get_by_id(db, facility_id)

    if not facility:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Health facility not found"
        )

    if hard_delete:
        await health_facility_service.hard_delete(db, facility)
        logger.warning(
            "Health facility permanently deleted: %s by admin %s",
            facility.id,
            _admin.username,
        )
    else:
        await health_facility_service.delete(db, facility)
        logger.info(
            "Health facility deactivated: %s by admin %s", facility.id, _admin.username
        )

    await db.commit()
