from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.outfit import Outfit
from app.models.user import User
from app.models.wardrobe_item import WardrobeItem


class OutfitRepository:
    def get_user_by_id(self, session: Session, user_id: UUID) -> User | None:
        return session.get(User, user_id)

    def get_wardrobe_item_by_id(self, session: Session, item_id: UUID) -> WardrobeItem | None:
        return session.get(WardrobeItem, item_id)

    def create_outfit(
        self,
        session: Session,
        user_id: UUID,
        occasion: str,
        item_ids: list[str],
        rationale: dict[str, object],
    ) -> Outfit:
        outfit = Outfit(
            id=uuid4(),
            user_id=user_id,
            occasion=occasion,
            item_ids=item_ids,
            rationale=rationale,
        )
        session.add(outfit)
        return outfit

    def get_outfit_by_id(self, session: Session, outfit_id: UUID) -> Outfit | None:
        return session.get(Outfit, outfit_id)

    def list_outfits_by_user_id(
        self,
        session: Session,
        user_id: UUID,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[Outfit], int]:
        filters = Outfit.user_id == user_id
        total = session.scalar(select(func.count()).select_from(Outfit).where(filters)) or 0
        outfits = list(
            session.scalars(select(Outfit).where(filters).offset(offset).limit(limit)).all()
        )
        return outfits, total
