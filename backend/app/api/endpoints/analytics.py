"""
Analytics and data export endpoints for the admin dashboard.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_admin, require_role
from app.core.database import get_db
from app.models.admin import AdminRole, AdminUser
from app.models.user import StudyGroup
from app.schemas.admin import DangerSignAlert, DashboardOverview, EngagementTrend
from app.services.analytics_service import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=DashboardOverview)
async def get_overview(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> DashboardOverview:
    """Get dashboard overview statistics."""
    return await analytics_service.get_dashboard_overview(db)


@router.get("/engagement-trends", response_model=list[EngagementTrend])
async def get_engagement_trends(
    weeks: int = Query(12, ge=1, le=52),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> list[EngagementTrend]:
    """Get weekly engagement trend data."""
    return await analytics_service.get_engagement_trends(db, weeks)


@router.get("/danger-alerts", response_model=list[DangerSignAlert])
async def get_danger_alerts(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> list[DangerSignAlert]:
    """Get recent danger sign alerts."""
    return await analytics_service.get_danger_sign_alerts(db, limit)


@router.get("/export/conversations")
async def export_conversations(
    study_group: Optional[StudyGroup] = None,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_role(AdminRole.ADMIN, AdminRole.RESEARCHER)),
) -> StreamingResponse:
    """Export anonymized conversation data as CSV."""
    csv_data = await analytics_service.export_conversations_csv(db, study_group)
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=conversations_export.csv"},
    )


@router.get("/export/engagement")
async def export_engagement(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_role(AdminRole.ADMIN, AdminRole.RESEARCHER)),
) -> StreamingResponse:
    """Export engagement metrics as CSV."""
    csv_data = await analytics_service.export_engagement_csv(db)
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=engagement_export.csv"},
    )


@router.get("/export/assessments")
async def export_assessments(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_role(AdminRole.ADMIN, AdminRole.RESEARCHER)),
) -> StreamingResponse:
    """Export knowledge assessment data as CSV (SPSS-ready)."""
    csv_data = await analytics_service.export_assessments_csv(db)
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=assessments_export.csv"},
    )
