from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories.wardrobe_repository import WardrobeRepository
from app.schemas.gap_schema import GapResponse, WardrobeGap
from app.services.category_taxonomy import BOTTOM, ONEPIECE, SHOES, TOP, bucket_for


class GapService:
    """Identifies missing primary wardrobe buckets from existing metadata."""

    def __init__(self, wardrobe_repository: WardrobeRepository | None = None) -> None:
        self.wardrobe_repository = wardrobe_repository or WardrobeRepository()

    def analyze_gaps(self, session: Session, user_id: UUID) -> GapResponse:
        items = self.wardrobe_repository.list_all_items_by_user_id(session, user_id)
        buckets = {bucket_for(item.category) for item in items}

        gaps: list[WardrobeGap] = []

        # A dress or jumpsuit already covers both halves, so neither counts as
        # missing when the wardrobe has one.
        if ONEPIECE not in buckets:
            if TOP not in buckets:
                gaps.append(
                    WardrobeGap(
                        category="top",
                        priority="high",
                        reason="No tops available for a basic outfit.",
                    )
                )
            if BOTTOM not in buckets:
                gaps.append(
                    WardrobeGap(
                        category="bottom",
                        priority="high",
                        reason="No bottoms available for a basic outfit.",
                    )
                )

        if SHOES not in buckets:
            gaps.append(
                WardrobeGap(
                    category="shoes",
                    priority="high",
                    reason="No shoes available for a basic outfit.",
                )
            )

        return GapResponse(gaps=gaps)
