"""Link appointments to package records without discarding legacy references."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b84c7d91e205"
down_revision: Union[str, None] = "0e3c11c0d664"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "appointments",
        "package_id",
        new_column_name="legacy_package_id",
        existing_type=sa.String(length=100),
        existing_nullable=True,
    )
    op.add_column(
        "appointments",
        sa.Column("package_id", sa.Integer(), nullable=True),
    )
    op.create_index("ix_appointments_package_id", "appointments", ["package_id"])
    op.create_foreign_key(
        "fk_appointments_package_id_packages",
        "appointments",
        "packages",
        ["package_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute(
        sa.text(
            """
            UPDATE appointments AS appointment
            SET package_id = package.id
            FROM packages AS package
            WHERE package.id = CASE
                WHEN appointment.legacy_package_id ~ '^[1-9][0-9]*$'
                  AND length(appointment.legacy_package_id) <= 10
                THEN appointment.legacy_package_id::numeric
                ELSE NULL
            END
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE appointments
            SET legacy_package_id = package_id::text
            WHERE package_id IS NOT NULL AND legacy_package_id IS NULL
            """
        )
    )
    op.drop_constraint(
        "fk_appointments_package_id_packages",
        "appointments",
        type_="foreignkey",
    )
    op.drop_index("ix_appointments_package_id", table_name="appointments")
    op.drop_column("appointments", "package_id")
    op.alter_column(
        "appointments",
        "legacy_package_id",
        new_column_name="package_id",
        existing_type=sa.String(length=100),
        existing_nullable=True,
    )
