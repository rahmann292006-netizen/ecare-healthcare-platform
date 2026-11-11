"""Add health package subscriptions and allow rebooking cancelled slots."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d9f3a761c482"
down_revision: Union[str, None] = "b84c7d91e205"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("packages", sa.Column("min_age_years", sa.Integer(), nullable=True))
    op.add_column("packages", sa.Column("max_age_years", sa.Integer(), nullable=True))
    op.add_column("packages", sa.Column("validity_period", sa.String(length=20), nullable=True))
    op.add_column("packages", sa.Column("validity_description", sa.Text(), nullable=True))
    op.create_check_constraint(
        "chk_packages_age_range",
        "packages",
        "(min_age_years IS NULL OR min_age_years BETWEEN 0 AND 130) AND "
        "(max_age_years IS NULL OR max_age_years BETWEEN 0 AND 130) AND "
        "(min_age_years IS NULL OR max_age_years IS NULL OR min_age_years <= max_age_years)",
    )
    op.create_check_constraint(
        "chk_packages_validity_period",
        "packages",
        "validity_period IS NULL OR validity_period IN ('monthly', 'quarterly', 'yearly')",
    )

    op.drop_constraint("uq_appointment_doctor_slot", "appointments", type_="unique")
    op.create_index(
        "uq_appointment_doctor_slot_active",
        "appointments",
        ["doctor_id", "appointment_date", "appointment_time"],
        unique=True,
        postgresql_where=sa.text("status <> 'cancelled'"),
    )

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("family_member_id", sa.Integer(), nullable=True),
        sa.Column("age_years_at_start", sa.Integer(), nullable=True),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(length=10), server_default="INR", nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="pending_payment", nullable=False),
        sa.Column("payment_status", sa.String(length=30), server_default="pending", nullable=False),
        sa.Column("renewal_of_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("amount >= 0", name="chk_subscriptions_amount_non_negative"),
        sa.CheckConstraint(
            "age_years_at_start IS NULL OR age_years_at_start BETWEEN 0 AND 130",
            name="chk_subscriptions_age_non_negative",
        ),
        sa.CheckConstraint("expires_at > start_at", name="chk_subscriptions_valid_dates"),
        sa.CheckConstraint(
            "status IN ('pending_payment', 'scheduled', 'active', 'expired', 'cancelled')",
            name="chk_subscriptions_status",
        ),
        sa.CheckConstraint(
            "payment_status IN ('pending', 'simulated', 'paid', 'failed', 'refunded')",
            name="chk_subscriptions_payment_status",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["packages.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["family_member_id"], ["family_members.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["renewal_of_id"], ["subscriptions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("renewal_of_id", name="uq_subscriptions_renewal_of_id"),
    )
    op.create_index("ix_subscriptions_id", "subscriptions", ["id"], unique=False)
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"], unique=False)
    op.create_index("ix_subscriptions_plan_id", "subscriptions", ["plan_id"], unique=False)
    op.create_index("ix_subscriptions_family_member_id", "subscriptions", ["family_member_id"], unique=False)
    op.create_index("ix_subscriptions_expires_at", "subscriptions", ["expires_at"], unique=False)
    op.create_index("ix_subscriptions_status", "subscriptions", ["status"], unique=False)
    op.create_index("ix_subscriptions_payment_status", "subscriptions", ["payment_status"], unique=False)
    op.create_index("ix_subscriptions_user_status", "subscriptions", ["user_id", "status"], unique=False)
    op.create_index(
        "uq_subscription_user_plan_open",
        "subscriptions",
        ["user_id", "plan_id"],
        unique=True,
        postgresql_where=sa.text(
            "renewal_of_id IS NULL AND status IN ('pending_payment', 'scheduled', 'active')"
        ),
    )

    op.create_table(
        "subscription_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subscription_id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("previous_status", sa.String(length=30), nullable=True),
        sa.Column("new_status", sa.String(length=30), nullable=False),
        sa.Column("payment_status", sa.String(length=30), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "event_type IN ('created', 'activated', 'payment_simulated', 'payment_confirmed', "
            "'payment_failed', 'renewed', 'cancelled', 'expired')",
            name="chk_subscription_events_type",
        ),
        sa.CheckConstraint(
            "new_status IN ('pending_payment', 'scheduled', 'active', 'expired', 'cancelled')",
            name="chk_subscription_events_status",
        ),
        sa.CheckConstraint(
            "payment_status IN ('pending', 'simulated', 'paid', 'failed', 'refunded')",
            name="chk_subscription_events_payment_status",
        ),
        sa.CheckConstraint("amount >= 0", name="chk_subscription_events_amount_non_negative"),
        sa.ForeignKeyConstraint(["subscription_id"], ["subscriptions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_subscription_events_id", "subscription_events", ["id"], unique=False)
    op.create_index("ix_subscription_events_subscription_id", "subscription_events", ["subscription_id"], unique=False)
    op.create_index(
        "ix_subscription_events_created_at",
        "subscription_events",
        ["subscription_id", "created_at"],
        unique=False,
    )

    op.alter_column(
        "reminders",
        "family_member_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.add_column("reminders", sa.Column("subscription_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_reminders_subscription_id_subscriptions",
        "reminders",
        "subscriptions",
        ["subscription_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_unique_constraint(
        "uq_reminders_subscription_id",
        "reminders",
        ["subscription_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_reminders_subscription_id", "reminders", type_="unique")
    op.drop_constraint(
        "fk_reminders_subscription_id_subscriptions",
        "reminders",
        type_="foreignkey",
    )
    op.drop_column("reminders", "subscription_id")
    op.alter_column(
        "reminders",
        "family_member_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.drop_index("ix_subscription_events_created_at", table_name="subscription_events")
    op.drop_index("ix_subscription_events_subscription_id", table_name="subscription_events")
    op.drop_index("ix_subscription_events_id", table_name="subscription_events")
    op.drop_table("subscription_events")

    op.drop_index("uq_subscription_user_plan_open", table_name="subscriptions")
    op.drop_index("ix_subscriptions_user_status", table_name="subscriptions")
    op.drop_index("ix_subscriptions_payment_status", table_name="subscriptions")
    op.drop_index("ix_subscriptions_status", table_name="subscriptions")
    op.drop_index("ix_subscriptions_expires_at", table_name="subscriptions")
    op.drop_index("ix_subscriptions_family_member_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_plan_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_user_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_id", table_name="subscriptions")
    op.drop_table("subscriptions")

    op.drop_index("uq_appointment_doctor_slot_active", table_name="appointments")
    op.create_unique_constraint(
        "uq_appointment_doctor_slot",
        "appointments",
        ["doctor_id", "appointment_date", "appointment_time"],
    )

    op.drop_constraint("chk_packages_validity_period", "packages", type_="check")
    op.drop_constraint("chk_packages_age_range", "packages", type_="check")
    op.drop_column("packages", "validity_description")
    op.drop_column("packages", "validity_period")
    op.drop_column("packages", "max_age_years")
    op.drop_column("packages", "min_age_years")
