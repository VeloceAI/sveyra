"""make media_assets.reference unique

Revision ID: 0007_media_asset_reference_unique
Revises: 0006_user_password_hash
Create Date: 2026-09-03
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0007_media_asset_reference_unique"
down_revision: str | None = "0006_user_password_hash"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_media_assets_reference",
        "media_assets",
        ["reference"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_media_assets_reference", "media_assets", type_="unique")
