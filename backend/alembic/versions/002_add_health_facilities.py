"""Add health facilities table

Revision ID: 002
Revises: 001
Create Date: 2026-02-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    facilitytype = postgresql.ENUM(
        "hospital", "health_center", "dispensary", "clinic", "maternity_home",
        name="facilitytype", create_type=False,
    )
    facilitylevel = postgresql.ENUM(
        "level_1", "level_2", "level_3", "level_4", "level_5", "level_6",
        name="facilitylevel", create_type=False,
    )

    facilitytype.create(op.get_bind(), checkfirst=True)
    facilitylevel.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "health_facilities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("facility_type", facilitytype, nullable=False),
        sa.Column("facility_level", facilitylevel, nullable=True),
        # Contact
        sa.Column("phone_number", sa.String(50), nullable=True),
        sa.Column("emergency_line", sa.String(50), nullable=True),
        sa.Column("email", sa.String(100), nullable=True),
        # Location
        sa.Column("county", sa.String(100), nullable=False),
        sa.Column("sub_county", sa.String(100), nullable=True),
        sa.Column("ward", sa.String(100), nullable=True),
        sa.Column("physical_address", sa.Text, nullable=True),
        sa.Column("latitude", sa.Float, nullable=True),
        sa.Column("longitude", sa.Float, nullable=True),
        # Services
        sa.Column("has_maternity_services", sa.Boolean, server_default=sa.text("true")),
        sa.Column("has_emergency_services", sa.Boolean, server_default=sa.text("true")),
        sa.Column("has_24h_services", sa.Boolean, server_default=sa.text("false")),
        sa.Column("has_ambulance", sa.Boolean, server_default=sa.text("false")),
        # Status
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("is_verified", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("display_priority", sa.Integer, nullable=False, server_default="100"),
        # Additional
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("website_url", sa.String(200), nullable=True),
        # Metadata
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_health_facilities_county", "health_facilities", ["county"])
    op.create_index("ix_health_facilities_active_emergency", "health_facilities", ["is_active", "has_emergency_services"])


def downgrade() -> None:
    op.drop_table("health_facilities")
    op.execute("DROP TYPE IF EXISTS facilitylevel")
    op.execute("DROP TYPE IF EXISTS facilitytype")
