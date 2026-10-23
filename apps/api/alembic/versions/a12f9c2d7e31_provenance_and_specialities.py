"""Add provider provenance and structured specialities.

Revision ID: a12f9c2d7e31
Revises: 6b3a5840da92
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a12f9c2d7e31"
down_revision: Union[str, None] = "6b3a5840da92"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PROVIDERS = ("hospitals", "doctors", "diagnostic_labs")


def upgrade() -> None:
    for table in PROVIDERS:
        op.add_column(table, sa.Column("source", sa.String(500), nullable=True))
        op.add_column(table, sa.Column("source_url", sa.String(1000), nullable=True))
        op.add_column(table, sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
        op.add_column(table, sa.Column("is_verified", sa.Boolean(), server_default=sa.false(), nullable=False))
        op.add_column(table, sa.Column("is_demo", sa.Boolean(), server_default=sa.false(), nullable=False))
        op.create_index(f"ix_{table}_is_verified", table, ["is_verified"])
        op.create_index(f"ix_{table}_is_demo", table, ["is_demo"])
        op.create_check_constraint(
            f"chk_{table}_verified_provenance", table,
            "NOT is_verified OR (verified_at IS NOT NULL AND source IS NOT NULL AND length(trim(source)) > 0)",
        )
        op.create_check_constraint(f"chk_{table}_demo_unverified", table, "NOT (is_demo AND is_verified)")

    op.create_table(
        "specialities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(140), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("name", name="uq_specialities_name"),
        sa.UniqueConstraint("slug", name="uq_specialities_slug"),
    )
    op.create_index("ix_specialities_is_active", "specialities", ["is_active"])
    op.create_table(
        "hospital_specialities",
        sa.Column("hospital_id", sa.Integer(), sa.ForeignKey("hospitals.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("speciality_id", sa.Integer(), sa.ForeignKey("specialities.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_index("ix_hospital_specialities_speciality_id", "hospital_specialities", ["speciality_id"])
    op.create_table(
        "doctor_specialities",
        sa.Column("doctor_id", sa.Integer(), sa.ForeignKey("doctors.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("speciality_id", sa.Integer(), sa.ForeignKey("specialities.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_index("ix_doctor_specialities_speciality_id", "doctor_specialities", ["speciality_id"])


def downgrade() -> None:
    op.drop_index("ix_doctor_specialities_speciality_id", table_name="doctor_specialities")
    op.drop_table("doctor_specialities")
    op.drop_index("ix_hospital_specialities_speciality_id", table_name="hospital_specialities")
    op.drop_table("hospital_specialities")
    op.drop_index("ix_specialities_is_active", table_name="specialities")
    op.drop_table("specialities")
    for table in reversed(PROVIDERS):
        op.drop_constraint(f"chk_{table}_demo_unverified", table, type_="check")
        op.drop_constraint(f"chk_{table}_verified_provenance", table, type_="check")
        op.drop_index(f"ix_{table}_is_demo", table_name=table)
        op.drop_index(f"ix_{table}_is_verified", table_name=table)
        for column in ("is_demo", "is_verified", "verified_at", "source_url", "source"):
            op.drop_column(table, column)
