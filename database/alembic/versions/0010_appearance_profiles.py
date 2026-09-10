"""add appearance_profiles

Revision ID: 0010_appearance_profiles
Revises: 0009_wear_logs
Create Date: 2026-09-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_appearance_profiles"
down_revision: str | None = "0009_wear_logs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "appearance_profiles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("skin", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("face", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("eyes", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("hair", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("colour_analysis", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("makeup", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("evidence", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.UniqueConstraint("user_id", name="uq_appearance_profiles_user_id"),
    )


def downgrade() -> None:
    op.drop_table("appearance_profiles")
