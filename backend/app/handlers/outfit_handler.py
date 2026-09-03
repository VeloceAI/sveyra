from uuid import UUID

from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.common import DEFAULT_LIST_LIMIT
from app.schemas.outfit_schema import OutfitCreateRequest, OutfitListResponse, OutfitResponse
from app.services.outfit_service import OutfitService


def create_outfit(
    payload: OutfitCreateRequest, session: Session, user: User
) -> OutfitResponse:
    service = OutfitService()
    return service.create_outfit(session, user.id, payload)


def get_outfit(outfit_id: UUID, session: Session, user: User) -> OutfitResponse:
    service = OutfitService()
    return service.get_outfit(session, outfit_id, user.id)


def list_outfits(
    session: Session,
    user: User,
    *,
    limit: int = DEFAULT_LIST_LIMIT,
    offset: int = 0,
) -> OutfitListResponse:
    service = OutfitService()
    return service.list_outfits(session, user.id, limit=limit, offset=offset)
