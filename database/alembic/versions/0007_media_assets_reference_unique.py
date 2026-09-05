"""add unique constraint on media_assets.reference

Revision ID: 0007_media_assets_reference_unique
Revises: 0006_user_password_hash
Create Date: 2026-09-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_media_assets_reference_unique"
down_revision: str | None = "0006_user_password_hash"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _find_duplicate_references(connection: sa.Connection) -> list[str]:
    rows = connection.execute(
        sa.text(
            """
            SELECT reference
            FROM media_assets
            GROUP BY reference
            HAVING COUNT(*) > 1
            """
        )
    ).fetchall()
    return [row.reference for row in rows]


def upgrade() -> None:
    connection = op.get_bind()
    duplicates = _find_duplicate_references(connection)
    if duplicates:
        sample = ", ".join(repr(reference) for reference in duplicates[:10])
        extra = "" if len(duplicates) <= 10 else f" (and {len(duplicates) - 10} more)"
        raise RuntimeError(
            "Migration 0007 cannot add uq_media_assets_reference because duplicate "
            f"media_assets.reference values exist: {sample}{extra}. "
            "Resolve duplicates manually before re-running this migration. "
            "No rows were deleted or modified."
        )
    op.create_unique_constraint(
        "uq_media_assets_reference",
        "media_assets",
        ["reference"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_media_assets_reference", "media_assets", type_="unique")
