"""add outfits

Revision ID: 0005_outfits
Revises: 0004_media_assets
Create Date: 2026-08-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_outfits"
down_revision: str | None = "0004_media_assets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "outfits",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("occasion", sa.Text(), nullable=False),
        sa.Column("item_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("rationale", sa.JSON(), nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_table("outfits")
