"""Add profile phone, doctor ownership, schedules, demo appointments and invoices."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1d2a3b4c5d6"
down_revision: Union[str, None] = "19c8bf6f362c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("phone", sa.String(length=50), nullable=True))
    op.add_column("users", sa.Column("provider_listing_id", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("provider_listing_type", sa.String(length=30), nullable=True))
    op.add_column("users", sa.Column("provider_doctor_id", sa.Integer(), nullable=True))
    op.create_index("ix_users_provider_doctor_id", "users", ["provider_doctor_id"], unique=True)
    op.create_index("ix_users_provider_listing_id", "users", ["provider_listing_id"], unique=False)
    op.create_foreign_key("fk_users_provider_doctor_id_doctors", "users", "doctors", ["provider_doctor_id"], ["id"], ondelete="SET NULL")
    op.add_column("doctors", sa.Column("schedule_json", sa.JSON(), nullable=True))

    op.create_table(
        "appointments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("reference", sa.String(length=40), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("doctor_id", sa.Integer(), nullable=False),
        sa.Column("appointment_date", sa.Date(), nullable=False),
        sa.Column("appointment_time", sa.Time(), nullable=False),
        sa.Column("location", sa.Text(), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("state", sa.String(length=100), nullable=False),
        sa.Column("package_id", sa.String(length=100), nullable=True),
        sa.Column("package_name", sa.String(length=255), nullable=True),
        sa.Column("package_amount", sa.Numeric(10, 2), server_default="0", nullable=False),
        sa.Column("consultation_fee", sa.Numeric(10, 2), server_default="0", nullable=False),
        sa.Column("service_charge", sa.Numeric(10, 2), server_default="0", nullable=False),
        sa.Column("total_amount", sa.Numeric(10, 2), server_default="0", nullable=False),
        sa.Column("advance_paid", sa.Numeric(10, 2), server_default="0", nullable=False),
        sa.Column("remaining_balance", sa.Numeric(10, 2), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=30), server_default="demo_confirmed", nullable=False),
        sa.Column("payment_status", sa.String(length=30), server_default="demo_unpaid", nullable=False),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('demo_confirmed', 'pending', 'completed', 'cancelled')", name="chk_appointments_status"),
        sa.CheckConstraint("payment_status IN ('demo_unpaid', 'demo_recorded', 'paid', 'refunded')", name="chk_appointments_payment_status"),
        sa.CheckConstraint("package_amount >= 0 AND consultation_fee >= 0 AND service_charge >= 0 AND total_amount >= 0 AND advance_paid >= 0 AND remaining_balance >= 0", name="chk_appointments_amounts_non_negative"),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reference"),
    )
    for column in ("id", "reference", "user_id", "doctor_id", "appointment_date", "city", "status", "is_demo"):
        op.create_index(f"ix_appointments_{column}", "appointments", [column], unique=column == "reference")
    op.create_index("ix_appointments_doctor_schedule", "appointments", ["doctor_id", "appointment_date", "appointment_time"], unique=False)

    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invoice_number", sa.String(length=40), nullable=False),
        sa.Column("appointment_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("package_amount", sa.Numeric(10, 2), server_default="0", nullable=False),
        sa.Column("consultation_fee", sa.Numeric(10, 2), server_default="0", nullable=False),
        sa.Column("service_charge", sa.Numeric(10, 2), server_default="0", nullable=False),
        sa.Column("total_amount", sa.Numeric(10, 2), server_default="0", nullable=False),
        sa.Column("advance_paid", sa.Numeric(10, 2), server_default="0", nullable=False),
        sa.Column("outstanding_balance", sa.Numeric(10, 2), server_default="0", nullable=False),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invoice_number"),
        sa.UniqueConstraint("appointment_id"),
    )
    for column in ("id", "invoice_number", "appointment_id", "user_id"):
        op.create_index(f"ix_invoices_{column}", "invoices", [column], unique=column in ("invoice_number", "appointment_id"))

    op.create_table(
        "payment_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("appointment_id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), server_default="0", nullable=False),
        sa.Column("method_label", sa.String(length=50), server_default="demo", nullable=False),
        sa.Column("status", sa.String(length=30), server_default="demo_not_charged", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("id", "user_id", "appointment_id", "invoice_id"):
        op.create_index(f"ix_payment_records_{column}", "payment_records", [column], unique=False)

    op.create_table(
        "doctor_applications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("doctor_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="chk_doctor_applications_status"),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("doctor_id"),
    )
    for column in ("id", "user_id", "doctor_id", "status"):
        op.create_index(f"ix_doctor_applications_{column}", "doctor_applications", [column], unique=column == "doctor_id")


def downgrade() -> None:
    for column in ("id", "user_id", "doctor_id", "status"):
        op.drop_index(f"ix_doctor_applications_{column}", table_name="doctor_applications")
    op.drop_table("doctor_applications")
    for column in ("id", "user_id", "appointment_id", "invoice_id"):
        op.drop_index(f"ix_payment_records_{column}", table_name="payment_records")
    op.drop_table("payment_records")
    for column in ("id", "invoice_number", "appointment_id", "user_id"):
        op.drop_index(f"ix_invoices_{column}", table_name="invoices")
    op.drop_table("invoices")
    op.drop_index("ix_appointments_doctor_schedule", table_name="appointments")
    for column in ("id", "reference", "user_id", "doctor_id", "appointment_date", "city", "status", "is_demo"):
        op.drop_index(f"ix_appointments_{column}", table_name="appointments")
    op.drop_table("appointments")
    op.drop_column("doctors", "schedule_json")
    op.drop_constraint("fk_users_provider_doctor_id_doctors", "users", type_="foreignkey")
    op.drop_index("ix_users_provider_listing_id", table_name="users")
    op.drop_index("ix_users_provider_doctor_id", table_name="users")
    op.drop_column("users", "provider_doctor_id")
    op.drop_column("users", "provider_listing_type")
    op.drop_column("users", "provider_listing_id")
    op.drop_column("users", "phone")
