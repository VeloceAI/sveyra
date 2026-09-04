"""add wear_logs

Revision ID: 0009_wear_logs
Revises: 0008_refresh_tokens
Create Date: 2026-09-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_wear_logs"
down_revision: str | None = "0008_refresh_tokens"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "wear_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("worn_on", sa.Date(), nullable=False),
        sa.Column("outfit_id", sa.Uuid(), sa.ForeignKey("outfits.id"), nullable=True),
        sa.Column("item_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("occasion", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("planned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        # One entry per user per day: a calendar cell holds one outfit.
        sa.UniqueConstraint("user_id", "worn_on", name="uq_wear_logs_user_date"),
    )
    op.create_index("ix_wear_logs_user_date", "wear_logs", ["user_id", "worn_on"])


def downgrade() -> None:
    op.drop_index("ix_wear_logs_user_date", table_name="wear_logs")
    op.drop_table("wear_logs")
