"""add family reminders

Revision ID: 48ca9ced0ad6
Revises: a6b8d0e2f4c1
Create Date: 2026-11-04 07:59:25.468941
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '48ca9ced0ad6'
down_revision: Union[str, None] = 'a6b8d0e2f4c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'family_members',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('relationship_type', sa.String(length=30), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint(
            "relationship_type IN ('self', 'father', 'mother', 'child', 'other')",
            name='chk_family_members_relationship',
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_index(op.f('ix_family_members_id'), 'family_members', ['id'], unique=False)
    op.create_index(op.f('ix_family_members_user_id'), 'family_members', ['user_id'], unique=False)

    op.create_table(
        'reminders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('family_member_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=30), nullable=False),
        sa.Column('reminder_date', sa.Date(), nullable=False),
        sa.Column('repeat_interval', sa.String(length=30), server_default='none', nullable=False),
        sa.Column('completed', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint(
            "category IN ('checkup', 'dental', 'vaccination', 'other')",
            name='chk_reminders_category',
        ),
        sa.CheckConstraint(
            "repeat_interval IN ('none', 'daily', 'weekly', 'monthly', 'yearly', 'half-yearly')",
            name='chk_reminders_repeat',
        ),
        sa.ForeignKeyConstraint(['family_member_id'], ['family_members.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_index(op.f('ix_reminders_family_member_id'), 'reminders', ['family_member_id'], unique=False)
    op.create_index(op.f('ix_reminders_id'), 'reminders', ['id'], unique=False)
    op.create_index(op.f('ix_reminders_reminder_date'), 'reminders', ['reminder_date'], unique=False)
    op.create_index(op.f('ix_reminders_user_id'), 'reminders', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_reminders_user_id'), table_name='reminders')
    op.drop_index(op.f('ix_reminders_reminder_date'), table_name='reminders')
    op.drop_index(op.f('ix_reminders_id'), table_name='reminders')
    op.drop_index(op.f('ix_reminders_family_member_id'), table_name='reminders')
    op.drop_table('reminders')

    op.drop_index(op.f('ix_family_members_user_id'), table_name='family_members')
    op.drop_index(op.f('ix_family_members_id'), table_name='family_members')
    op.drop_table('family_members')
