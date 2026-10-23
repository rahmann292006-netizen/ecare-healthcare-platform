"""Add standalone-capable OPD providers.

Revision ID: b37c1e8a42f0
Revises: a12f9c2d7e31
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b37c1e8a42f0"
down_revision: Union[str, None] = "a12f9c2d7e31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "opds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("opd_type", sa.String(100), nullable=True),
        sa.Column("hospital_id", sa.Integer(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("locality", sa.String(255), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("state", sa.String(100), nullable=True),
        sa.Column("pincode", sa.String(20), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("website", sa.String(500), nullable=True),
        sa.Column("operating_hours", sa.Text(), nullable=True),
        sa.Column("source", sa.String(500), nullable=True),
        sa.Column("source_url", sa.String(1000), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_verified", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("verification_status", sa.String(50), server_default="unverified", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["hospital_id"], ["hospitals.id"], ondelete="SET NULL"),
        sa.CheckConstraint("verification_status IN ('unverified', 'pending', 'verified', 'rejected')", name="chk_opds_verification_status"),
        sa.CheckConstraint("NOT is_verified OR (verified_at IS NOT NULL AND source IS NOT NULL AND length(trim(source)) > 0)", name="chk_opds_verified_provenance"),
        sa.CheckConstraint("NOT (is_demo AND is_verified)", name="chk_opds_demo_unverified"),
    )
    for column in ("id", "name", "hospital_id", "locality", "city", "state", "is_verified", "is_demo", "verification_status", "is_active"):
        op.create_index(f"ix_opds_{column}", "opds", [column])
    op.create_index("ix_opds_slug", "opds", ["slug"], unique=True)
    op.create_index("ix_opds_city_state", "opds", ["city", "state"])
    op.create_index("ix_opds_verification_active", "opds", ["verification_status", "is_active"])


def downgrade() -> None:
    op.drop_index("ix_opds_verification_active", table_name="opds")
    op.drop_index("ix_opds_city_state", table_name="opds")
    op.drop_index("ix_opds_slug", table_name="opds")
    for column in ("is_active", "verification_status", "is_demo", "is_verified", "state", "city", "locality", "hospital_id", "name", "id"):
        op.drop_index(f"ix_opds_{column}", table_name="opds")
    op.drop_table("opds")
