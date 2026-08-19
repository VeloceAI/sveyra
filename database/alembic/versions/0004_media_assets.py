"""add media_assets

Revision ID: 0004_media_assets
Revises: 0003_wardrobe_items
Create Date: 2026-08-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_media_assets"
down_revision: str | None = "0003_wardrobe_items"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "media_assets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("wardrobe_item_id", sa.Uuid(), sa.ForeignKey("wardrobe_items.id"), nullable=True),
        sa.Column("reference", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("media_assets")
