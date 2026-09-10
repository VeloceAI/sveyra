from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.appearance_profile import AppearanceProfile
from app.models.body_profile import BodyProfile
from app.models.style_profile import StyleProfile
from app.models.wardrobe_item import WardrobeItem


@dataclass(frozen=True)
class PersonalModelSnapshot:
    style_ready: bool
    appearance_ready: bool
    body_ready: bool
    body_measurement_count: int
    wardrobe_items: int
    enriched_items: int


class PlatformRepository:
    """Read-only queries for the signed-in product home."""

    def snapshot(self, session: Session, user_id: UUID) -> PersonalModelSnapshot:
        style_ready = (
            session.scalar(
                select(StyleProfile.id).where(StyleProfile.user_id == user_id).limit(1)
            )
            is not None
        )
        appearance_ready = (
            session.scalar(
                select(AppearanceProfile.id)
                .where(AppearanceProfile.user_id == user_id)
                .limit(1)
            )
            is not None
        )
        body_profiles = list(
            session.scalars(select(BodyProfile).where(BodyProfile.user_id == user_id)).all()
        )
        latest_body = body_profiles[-1] if body_profiles else None
        measurements = latest_body.measurements if latest_body is not None else {}
        measurement_count = sum(
            value is not None
            for value in measurements.values()
        ) if isinstance(measurements, dict) else 0

        wardrobe = list(
            session.scalars(
                select(WardrobeItem).where(WardrobeItem.user_id == user_id)
            ).all()
        )
        enriched = sum(
            isinstance(item.attributes, dict)
            and isinstance(item.attributes.get("cv"), dict)
            for item in wardrobe
        )
        return PersonalModelSnapshot(
            style_ready=style_ready,
            appearance_ready=appearance_ready,
            body_ready=measurement_count > 0,
            body_measurement_count=measurement_count,
            wardrobe_items=len(wardrobe),
            enriched_items=enriched,
        )
