"""
Analytics and research data service.

Provides engagement metrics, dashboard statistics, and data export functionality.
"""

import csv
import io
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import KnowledgeAssessment
from app.models.conversation import Conversation, MessageDirection
from app.models.engagement import EngagementMetric
from app.models.user import StudyGroup, User
from app.schemas.admin import (
    DangerSignAlert,
    DashboardOverview,
    EngagementTrend,
    TopicCount,
)

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for analytics, metrics, and data export."""

    @staticmethod
    async def get_dashboard_overview(db: AsyncSession) -> DashboardOverview:
        """Get the main dashboard overview statistics."""
        now = datetime.now(timezone.utc)
        seven_days_ago = now - timedelta(days=7)

        # Total users by study group
        total_result = await db.execute(select(func.count(User.id)))
        total_users = total_result.scalar() or 0

        intervention_result = await db.execute(
            select(func.count(User.id)).where(
                User.study_group == StudyGroup.INTERVENTION
            )
        )
        intervention_users = intervention_result.scalar() or 0

        control_result = await db.execute(
            select(func.count(User.id)).where(
                User.study_group == StudyGroup.CONTROL
            )
        )
        control_users = control_result.scalar() or 0

        # Active users in last 7 days
        active_result = await db.execute(
            select(func.count(func.distinct(Conversation.user_id))).where(
                Conversation.created_at >= seven_days_ago
            )
        )
        active_users = active_result.scalar() or 0

        # Total conversations in last 7 days
        conv_result = await db.execute(
            select(func.count(Conversation.id)).where(
                Conversation.created_at >= seven_days_ago
            )
        )
        total_conversations = conv_result.scalar() or 0

        # Danger sign alerts (unreviewed)
        danger_result = await db.execute(
            select(func.count(Conversation.id)).where(
                Conversation.danger_sign_detected.is_(True),
                Conversation.created_at >= seven_days_ago,
            )
        )
        danger_alerts = danger_result.scalar() or 0

        # Average response time
        avg_time_result = await db.execute(
            select(func.avg(Conversation.response_time_ms)).where(
                Conversation.response_time_ms.isnot(None),
                Conversation.created_at >= seven_days_ago,
            )
        )
        avg_response_time = avg_time_result.scalar()

        return DashboardOverview(
            total_users=total_users,
            intervention_users=intervention_users,
            control_users=control_users,
            active_users_7d=active_users,
            total_conversations_7d=total_conversations,
            danger_sign_alerts_pending=danger_alerts,
            avg_response_time_ms=float(avg_response_time) if avg_response_time else None,
        )

    @staticmethod
    async def get_engagement_trends(
        db: AsyncSession, weeks: int = 12
    ) -> list[EngagementTrend]:
        """Get weekly engagement trends."""
        trends = []
        now = datetime.now(timezone.utc)

        for week_offset in range(weeks - 1, -1, -1):
            week_start = now - timedelta(weeks=week_offset + 1)
            week_end = now - timedelta(weeks=week_offset)

            msg_result = await db.execute(
                select(func.count(Conversation.id)).where(
                    Conversation.created_at >= week_start,
                    Conversation.created_at < week_end,
                )
            )
            total_messages = msg_result.scalar() or 0

            user_result = await db.execute(
                select(func.count(func.distinct(Conversation.user_id))).where(
                    Conversation.created_at >= week_start,
                    Conversation.created_at < week_end,
                )
            )
            active_users = user_result.scalar() or 0

            avg_result = await db.execute(
                select(func.avg(Conversation.response_time_ms)).where(
                    Conversation.response_time_ms.isnot(None),
                    Conversation.created_at >= week_start,
                    Conversation.created_at < week_end,
                )
            )
            avg_time = avg_result.scalar()

            trends.append(
                EngagementTrend(
                    week=weeks - week_offset,
                    total_messages=total_messages,
                    active_users=active_users,
                    avg_response_time=float(avg_time) if avg_time else None,
                )
            )

        return trends

    @staticmethod
    async def get_danger_sign_alerts(
        db: AsyncSession, limit: int = 50
    ) -> list[DangerSignAlert]:
        """Get recent danger sign alerts with user info."""
        result = await db.execute(
            select(Conversation, User.phone_number)
            .join(User, Conversation.user_id == User.id)
            .where(Conversation.danger_sign_detected.is_(True))
            .order_by(Conversation.created_at.desc())
            .limit(limit)
        )

        alerts = []
        for conv, phone in result.all():
            alerts.append(
                DangerSignAlert(
                    id=conv.id,
                    user_id=conv.user_id,
                    phone_number=phone,
                    message_text=conv.message_text,
                    danger_sign_keywords=conv.danger_sign_keywords,
                    gestational_age=conv.gestational_age_at_message,
                    created_at=conv.created_at,
                )
            )
        return alerts

    @staticmethod
    async def export_conversations_csv(
        db: AsyncSession,
        study_group: Optional[StudyGroup] = None,
    ) -> str:
        """Export conversations as CSV string with anonymized IDs."""
        query = (
            select(
                User.id.label("user_id"),
                User.study_group,
                Conversation.message_direction,
                Conversation.message_text,
                Conversation.gestational_age_at_message,
                Conversation.danger_sign_detected,
                Conversation.danger_sign_keywords,
                Conversation.response_time_ms,
                Conversation.created_at,
            )
            .join(User, Conversation.user_id == User.id)
            .order_by(Conversation.created_at)
        )

        if study_group:
            query = query.where(User.study_group == study_group)

        result = await db.execute(query)
        rows = result.all()

        # Build anonymized ID mapping
        user_ids = list({str(row.user_id) for row in rows})
        id_map = {uid: f"STUDY_{i+1:04d}" for i, uid in enumerate(sorted(user_ids))}

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "study_id",
            "study_group",
            "direction",
            "message_text",
            "gestational_age",
            "danger_sign",
            "danger_keywords",
            "response_time_ms",
            "timestamp",
        ])

        for row in rows:
            writer.writerow([
                id_map[str(row.user_id)],
                row.study_group.value if row.study_group else "",
                row.message_direction.value if row.message_direction else "",
                row.message_text,
                row.gestational_age_at_message,
                row.danger_sign_detected,
                row.danger_sign_keywords or "",
                row.response_time_ms or "",
                row.created_at.isoformat() if row.created_at else "",
            ])

        return output.getvalue()

    @staticmethod
    async def export_engagement_csv(db: AsyncSession) -> str:
        """Export engagement metrics as CSV."""
        result = await db.execute(
            select(
                User.id.label("user_id"),
                User.study_group,
                EngagementMetric.week_number,
                EngagementMetric.messages_sent,
                EngagementMetric.messages_received,
                EngagementMetric.avg_response_time_seconds,
                EngagementMetric.active_days,
                EngagementMetric.topics_discussed,
                EngagementMetric.danger_signs_flagged,
            )
            .join(User, EngagementMetric.user_id == User.id)
            .order_by(User.id, EngagementMetric.week_number)
        )
        rows = result.all()

        user_ids = list({str(row.user_id) for row in rows})
        id_map = {uid: f"STUDY_{i+1:04d}" for i, uid in enumerate(sorted(user_ids))}

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "study_id",
            "study_group",
            "week",
            "messages_sent",
            "messages_received",
            "avg_response_time_s",
            "active_days",
            "topics_discussed",
            "danger_signs_flagged",
        ])

        for row in rows:
            writer.writerow([
                id_map.get(str(row.user_id), "UNKNOWN"),
                row.study_group.value if row.study_group else "",
                row.week_number,
                row.messages_sent,
                row.messages_received,
                row.avg_response_time_seconds or "",
                row.active_days,
                row.topics_discussed,
                row.danger_signs_flagged,
            ])

        return output.getvalue()

    @staticmethod
    async def export_assessments_csv(db: AsyncSession) -> str:
        """Export knowledge assessment data as CSV for SPSS analysis."""
        result = await db.execute(
            select(
                User.id.label("user_id"),
                User.study_group,
                User.gestational_age_at_enrollment,
                KnowledgeAssessment.assessment_type,
                KnowledgeAssessment.total_score,
                KnowledgeAssessment.max_score,
                KnowledgeAssessment.completed_at,
            )
            .join(User, KnowledgeAssessment.user_id == User.id)
            .order_by(User.id, KnowledgeAssessment.completed_at)
        )
        rows = result.all()

        user_ids = list({str(row.user_id) for row in rows})
        id_map = {uid: f"STUDY_{i+1:04d}" for i, uid in enumerate(sorted(user_ids))}

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "study_id",
            "study_group",
            "gestational_age_enrollment",
            "assessment_type",
            "total_score",
            "max_score",
            "completed_at",
        ])

        for row in rows:
            writer.writerow([
                id_map.get(str(row.user_id), "UNKNOWN"),
                row.study_group.value if row.study_group else "",
                row.gestational_age_at_enrollment or "",
                row.assessment_type.value if row.assessment_type else "",
                row.total_score,
                row.max_score,
                row.completed_at.isoformat() if row.completed_at else "",
            ])

        return output.getvalue()


analytics_service = AnalyticsService()
