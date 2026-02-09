"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-02-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enum types
    studygroup = postgresql.ENUM("intervention", "control", name="studygroup", create_type=False)
    messagedirection = postgresql.ENUM("incoming", "outgoing", name="messagedirection", create_type=False)
    assessmenttype = postgresql.ENUM("baseline", "endline", name="assessmenttype", create_type=False)
    adminrole = postgresql.ENUM("admin", "researcher", "clinical_reviewer", name="adminrole", create_type=False)

    studygroup.create(op.get_bind(), checkfirst=True)
    messagedirection.create(op.get_bind(), checkfirst=True)
    assessmenttype.create(op.get_bind(), checkfirst=True)
    adminrole.create(op.get_bind(), checkfirst=True)

    # Users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("phone_number", sa.String(20), unique=True, nullable=False),
        sa.Column("whatsapp_id", sa.String(50), unique=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=True),
        sa.Column("study_group", studygroup, nullable=False, server_default="intervention"),
        sa.Column("gestational_age_at_enrollment", sa.Integer, nullable=True),
        sa.Column("expected_delivery_date", sa.Date, nullable=True),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("is_active", sa.Boolean, default=True, server_default=sa.text("true")),
        sa.Column("language_preference", sa.String(10), nullable=False, server_default="en"),
        sa.Column("registration_complete", sa.Boolean, default=False, server_default=sa.text("false")),
        sa.Column("consent_given", sa.Boolean, default=False, server_default=sa.text("false")),
        sa.Column("consent_given_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Conversations
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("message_direction", messagedirection, nullable=False),
        sa.Column("message_text", sa.Text, nullable=False),
        sa.Column("gestational_age_at_message", sa.Integer, nullable=True),
        sa.Column("danger_sign_detected", sa.Boolean, default=False, server_default=sa.text("false")),
        sa.Column("danger_sign_keywords", sa.Text, nullable=True),
        sa.Column("response_time_ms", sa.Integer, nullable=True),
        sa.Column("ai_model_used", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])
    op.create_index("ix_conversations_created_at", "conversations", ["created_at"])

    # Knowledge Assessments
    op.create_table(
        "knowledge_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("assessment_type", assessmenttype, nullable=False),
        sa.Column("total_score", sa.Integer, nullable=False),
        sa.Column("max_score", sa.Integer, server_default="100"),
        sa.Column("responses", postgresql.JSON, nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_knowledge_assessments_user_id", "knowledge_assessments", ["user_id"])

    # Engagement Metrics
    op.create_table(
        "engagement_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("week_number", sa.Integer, nullable=False),
        sa.Column("messages_sent", sa.Integer, server_default="0"),
        sa.Column("messages_received", sa.Integer, server_default="0"),
        sa.Column("avg_response_time_seconds", sa.Float, nullable=True),
        sa.Column("active_days", sa.Integer, server_default="0"),
        sa.Column("topics_discussed", sa.Integer, server_default="0"),
        sa.Column("danger_signs_flagged", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_engagement_metrics_user_id", "engagement_metrics", ["user_id"])

    # Admin Users
    op.create_table(
        "admin_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("username", sa.String(100), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("role", adminrole, nullable=False, server_default="researcher"),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("admin_users")
    op.drop_table("engagement_metrics")
    op.drop_table("knowledge_assessments")
    op.drop_table("conversations")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS adminrole")
    op.execute("DROP TYPE IF EXISTS assessmenttype")
    op.execute("DROP TYPE IF EXISTS messagedirection")
    op.execute("DROP TYPE IF EXISTS studygroup")
