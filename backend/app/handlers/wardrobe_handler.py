from uuid import UUID

from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.common import DEFAULT_LIST_LIMIT
from app.schemas.wardrobe_schema import (
    WardrobeItemCreateRequest,
    WardrobeItemListResponse,
    WardrobeItemResponse,
    WardrobeItemUpdateRequest,
)
from app.services.garment_enrichment_service import GarmentEnrichmentService
from app.services.wardrobe_service import WardrobeService
from app.storage.port import StoragePort
from app.vision.port import VisionPort


def create_wardrobe_item(
    payload: WardrobeItemCreateRequest, session: Session, user: User
) -> WardrobeItemResponse:
    service = WardrobeService()
    return service.create_item(session, user.id, payload)


def get_wardrobe_item(
    item_id: UUID, session: Session, user: User
) -> WardrobeItemResponse:
    service = WardrobeService()
    return service.get_item(session, item_id, user.id)


def list_wardrobe_items(
    session: Session,
    user: User,
    *,
    limit: int = DEFAULT_LIST_LIMIT,
    offset: int = 0,
) -> WardrobeItemListResponse:
    service = WardrobeService()
    return service.list_items(session, user.id, limit=limit, offset=offset)


def update_wardrobe_item(
    item_id: UUID,
    payload: WardrobeItemUpdateRequest,
    session: Session,
    user: User,
) -> WardrobeItemResponse:
    service = WardrobeService()
    return service.update_item(session, item_id, user.id, payload)


def delete_wardrobe_item(
    item_id: UUID,
    session: Session,
    user: User,
    storage: StoragePort,
) -> None:
    service = WardrobeService(storage=storage)
    service.delete_item(session, item_id, user.id)


def enrich_wardrobe_item(
    item_id: UUID,
    session: Session,
    user: User,
    storage: StoragePort,
    vision: VisionPort,
) -> WardrobeItemResponse:
    service = GarmentEnrichmentService(storage=storage, vision=vision)
    return service.enrich_item(session, user.id, item_id)
