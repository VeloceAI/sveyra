from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories.wardrobe_repository import WardrobeRepository
from app.schemas.gap_schema import GapResponse, WardrobeGap
from app.services.recommendation_engine import BOTTOM_CATEGORIES, SHOE_CATEGORIES, TOP_CATEGORIES


def _normalize(value: str) -> str:
    return value.strip().lower()


def _has_bucket(categories: list[str], bucket: frozenset[str]) -> bool:
    return any(_normalize(c) in bucket for c in categories)


class GapService:
    """Identifies missing primary wardrobe buckets from existing metadata."""

    def __init__(self, wardrobe_repository: WardrobeRepository | None = None) -> None:
        self.wardrobe_repository = wardrobe_repository or WardrobeRepository()

    def analyze_gaps(self, session: Session, user_id: UUID) -> GapResponse:
        items = self.wardrobe_repository.list_all_items_by_user_id(session, user_id)
        categories = [item.category for item in items]

        gaps: list[WardrobeGap] = []

        if not _has_bucket(categories, TOP_CATEGORIES):
            gaps.append(
                WardrobeGap(
                    category="top",
                    priority="high",
                    reason="No tops available for a basic outfit.",
                )
            )

        if not _has_bucket(categories, BOTTOM_CATEGORIES):
            gaps.append(
                WardrobeGap(
                    category="bottom",
                    priority="high",
                    reason="No bottoms available for a basic outfit.",
                )
            )

        if not _has_bucket(categories, SHOE_CATEGORIES):
            gaps.append(
                WardrobeGap(
                    category="shoes",
                    priority="high",
                    reason="No shoes available for a basic outfit.",
                )
            )

        return GapResponse(gaps=gaps)
