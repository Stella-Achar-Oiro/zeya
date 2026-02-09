"""Health facility service for managing emergency contact information."""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.health_facility import HealthFacility
from app.schemas.health_facility import HealthFacilityCreate, HealthFacilityUpdate

logger = logging.getLogger(__name__)


class HealthFacilityService:
    """Service for managing health facilities."""

    async def get_by_id(
        self, db: AsyncSession, facility_id: UUID
    ) -> Optional[HealthFacility]:
        """Get a health facility by ID."""
        result = await db.execute(
            select(HealthFacility).where(HealthFacility.id == facility_id)
        )
        return result.scalar_one_or_none()

    async def get_by_county(
        self, db: AsyncSession, county: str, active_only: bool = True
    ) -> list[HealthFacility]:
        """Get all health facilities in a county."""
        query = select(HealthFacility).where(func.lower(HealthFacility.county) == county.lower())

        if active_only:
            query = query.where(HealthFacility.is_active == True)

        query = query.order_by(
            HealthFacility.display_priority.asc(), HealthFacility.name.asc()
        )

        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_emergency_facilities(
        self, db: AsyncSession, county: str, limit: int = 5
    ) -> list[HealthFacility]:
        """
        Get top emergency facilities for a county.

        Returns facilities that:
        - Are active
        - Have emergency services
        - Are verified
        - Ordered by priority then name
        """
        query = (
            select(HealthFacility)
            .where(
                func.lower(HealthFacility.county) == county.lower(),
                HealthFacility.is_active == True,
                HealthFacility.has_emergency_services == True,
                HealthFacility.is_verified == True,
            )
            .order_by(
                HealthFacility.display_priority.asc(), HealthFacility.name.asc()
            )
            .limit(limit)
        )

        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_all(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        county: Optional[str] = None,
        active_only: bool = False,
    ) -> tuple[list[HealthFacility], int]:
        """Get all health facilities with pagination."""
        query = select(HealthFacility)

        if county:
            query = query.where(func.lower(HealthFacility.county) == county.lower())

        if active_only:
            query = query.where(HealthFacility.is_active == True)

        # Get total count
        count_query = select(func.count()).select_from(HealthFacility)
        if county:
            count_query = count_query.where(func.lower(HealthFacility.county) == county.lower())
        if active_only:
            count_query = count_query.where(HealthFacility.is_active == True)

        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Get paginated results
        query = (
            query.order_by(
                HealthFacility.display_priority.asc(), HealthFacility.name.asc()
            )
            .offset(skip)
            .limit(limit)
        )

        result = await db.execute(query)
        facilities = list(result.scalars().all())

        return facilities, total

    async def create(
        self, db: AsyncSession, facility_data: HealthFacilityCreate
    ) -> HealthFacility:
        """Create a new health facility."""
        facility = HealthFacility(**facility_data.model_dump())
        db.add(facility)
        await db.flush()
        await db.refresh(facility)
        logger.info("Created health facility: %s (%s)", facility.name, facility.county)
        return facility

    async def update(
        self,
        db: AsyncSession,
        facility: HealthFacility,
        facility_data: HealthFacilityUpdate,
    ) -> HealthFacility:
        """Update a health facility."""
        update_data = facility_data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(facility, field, value)

        await db.flush()
        await db.refresh(facility)
        logger.info("Updated health facility: %s", facility.id)
        return facility

    async def delete(self, db: AsyncSession, facility: HealthFacility) -> None:
        """Soft delete a health facility (mark as inactive)."""
        facility.is_active = False
        await db.flush()
        logger.info("Deactivated health facility: %s", facility.id)

    async def hard_delete(self, db: AsyncSession, facility: HealthFacility) -> None:
        """Permanently delete a health facility."""
        await db.delete(facility)
        await db.flush()
        logger.info("Permanently deleted health facility: %s", facility.id)

    def format_emergency_message(
        self, facilities: list[HealthFacility], language: str = "en"
    ) -> str:
        """Format emergency message with facility contacts."""
        if not facilities:
            if language == "sw":
                return "Tafadhali nenda hospitali iliyo karibu nawe."
            return "Please go to your nearest health facility."

        if language == "sw":
            header = "Hospitali za karibu:\n"
        else:
            header = "Nearest facilities:\n"

        facility_lines = [
            facility.format_for_emergency_response() for facility in facilities
        ]

        return header + "\n".join(facility_lines)


health_facility_service = HealthFacilityService()
