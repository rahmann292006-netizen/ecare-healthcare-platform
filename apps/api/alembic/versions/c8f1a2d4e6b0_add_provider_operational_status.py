"""Represent provider operational status and unknown service flags.

Revision ID: c8f1a2d4e6b0
Revises: b37c1e8a42f0
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c8f1a2d4e6b0"
down_revision: Union[str, None] = "b37c1e8a42f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PROVIDER_TABLES = ("hospitals", "doctors", "diagnostic_labs", "opds")


def upgrade() -> None:
    # The server default backfills every existing row as unknown and also
    # protects inserts from clients that do not yet send this field.
    for table in PROVIDER_TABLES:
        op.add_column(
            table,
            sa.Column(
                "operational_status",
                sa.String(length=30),
                server_default="unknown",
                nullable=False,
            ),
        )
        op.create_index(
            f"ix_{table}_operational_status", table, ["operational_status"]
        )
        op.create_check_constraint(
            f"chk_{table}_operational_status",
            table,
            "operational_status IN ('unknown', 'operational', 'not_operational')",
        )

    # Preserve existing booleans while allowing future unknown values.
    op.alter_column(
        "hospitals",
        "emergency_services",
        existing_type=sa.Boolean(),
        nullable=True,
        server_default=None,
    )
    op.alter_column(
        "diagnostic_labs",
        "home_sample_collection",
        existing_type=sa.Boolean(),
        nullable=True,
        server_default=None,
    )


def downgrade() -> None:
    # A downgrade maps NULL service flags to false because the old schema
    # cannot represent unknown. This is necessarily lossy.
    op.execute(
        "UPDATE hospitals SET emergency_services = false WHERE emergency_services IS NULL"
    )
    op.execute(
        "UPDATE diagnostic_labs SET home_sample_collection = false "
        "WHERE home_sample_collection IS NULL"
    )
    op.alter_column(
        "hospitals",
        "emergency_services",
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.false(),
    )
    op.alter_column(
        "diagnostic_labs",
        "home_sample_collection",
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.false(),
    )
    for table in reversed(PROVIDER_TABLES):
        op.drop_constraint(
            f"chk_{table}_operational_status", table, type_="check"
        )
        op.drop_index(f"ix_{table}_operational_status", table_name=table)
        op.drop_column(table, "operational_status")
