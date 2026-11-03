"""Prevent duplicate booking slots and demo payments."""

from typing import Sequence, Union

from alembic import op


revision: str = "a6b8d0e2f4c1"
down_revision: Union[str, None] = "f1d2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_appointment_doctor_slot",
        "appointments",
        ["doctor_id", "appointment_date", "appointment_time"],
    )
    op.create_unique_constraint(
        "uq_payment_appointment",
        "payment_records",
        ["appointment_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_payment_appointment", "payment_records", type_="unique")
    op.drop_constraint("uq_appointment_doctor_slot", "appointments", type_="unique")
