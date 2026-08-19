from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import OutfitNotFoundError, UserNotFoundError, WardrobeItemNotFoundError
from app.models.outfit import Outfit
from app.repositories.outfit_repository import OutfitRepository
from app.schemas.outfit_schema import OutfitCreateRequest, OutfitListResponse, OutfitResponse


class OutfitService:
    def __init__(self, repository: OutfitRepository | None = None) -> None:
        self.repository = repository or OutfitRepository()

    def create_outfit(
        self, session: Session, user_id: UUID, payload: OutfitCreateRequest
    ) -> OutfitResponse:
        user = self.repository.get_user_by_id(session, user_id)
        if user is None:
            raise UserNotFoundError
        for item_id in payload.item_ids:
            item = self.repository.get_wardrobe_item_by_id(session, item_id)
            if item is None or item.user_id != user_id:
                raise WardrobeItemNotFoundError
        outfit = self.repository.create_outfit(
            session,
            user_id,
            payload.occasion,
            [str(item_id) for item_id in payload.item_ids],
            payload.rationale,
        )
        session.commit()
        session.refresh(outfit)
        return self._to_response(outfit)

    def get_outfit(self, session: Session, outfit_id: UUID, user_id: UUID) -> OutfitResponse:
        outfit = self.repository.get_outfit_by_id(session, outfit_id)
        if outfit is None or outfit.user_id != user_id:
            raise OutfitNotFoundError
        return self._to_response(outfit)

    def list_outfits(
        self, session: Session, user_id: UUID, *, limit: int, offset: int
    ) -> OutfitListResponse:
        user = self.repository.get_user_by_id(session, user_id)
        if user is None:
            raise UserNotFoundError
        outfits, total = self.repository.list_outfits_by_user_id(
            session, user_id, limit=limit, offset=offset
        )
        return OutfitListResponse(
            outfits=[self._to_response(outfit) for outfit in outfits],
            limit=limit,
            offset=offset,
            total=total,
        )

    def _to_response(self, outfit: Outfit) -> OutfitResponse:
        return OutfitResponse(
            id=outfit.id,
            user_id=outfit.user_id,
            occasion=outfit.occasion,
            item_ids=[UUID(str(item_id)) for item_id in outfit.item_ids],
            rationale=outfit.rationale,
        )
