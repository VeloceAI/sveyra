from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db.session import get_db
from app.handlers.wardrobe_handler import (
    create_wardrobe_item,
    delete_wardrobe_item,
    enrich_wardrobe_item,
    get_wardrobe_item,
    list_wardrobe_items,
    update_wardrobe_item,
)
from app.models.user import User
from app.schemas.common import DEFAULT_LIST_LIMIT, MAX_LIST_LIMIT
from app.schemas.wardrobe_schema import (
    WardrobeItemCreateRequest,
    WardrobeItemListResponse,
    WardrobeItemResponse,
    WardrobeItemUpdateRequest,
)
from app.storage.deps import get_storage
from app.storage.port import StoragePort
from app.vision.deps import get_vision
from app.vision.port import VisionPort

router = APIRouter(prefix="/wardrobe", tags=["wardrobe"])


@router.post("", response_model=WardrobeItemResponse)
def create_item(
    payload: WardrobeItemCreateRequest,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WardrobeItemResponse:
    return create_wardrobe_item(payload, session, user)


@router.get("", response_model=WardrobeItemListResponse)
def list_items(
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = Query(default=DEFAULT_LIST_LIMIT, ge=1, le=MAX_LIST_LIMIT),
    offset: int = Query(default=0, ge=0),
) -> WardrobeItemListResponse:
    return list_wardrobe_items(session, user, limit=limit, offset=offset)


@router.post("/{item_id}/enrich", response_model=WardrobeItemResponse)
def enrich_item(
    item_id: UUID,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    storage: StoragePort = Depends(get_storage),
    vision: VisionPort = Depends(get_vision),
) -> WardrobeItemResponse:
    return enrich_wardrobe_item(item_id, session, user, storage, vision)


@router.patch("/{item_id}", response_model=WardrobeItemResponse)
def patch_item(
    item_id: UUID,
    payload: WardrobeItemUpdateRequest,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WardrobeItemResponse:
    return update_wardrobe_item(item_id, payload, session, user)


@router.delete("/{item_id}", status_code=204)
def remove_item(
    item_id: UUID,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    storage: StoragePort = Depends(get_storage),
) -> Response:
    delete_wardrobe_item(item_id, session, user, storage)
    return Response(status_code=204)


@router.get("/{item_id}", response_model=WardrobeItemResponse)
def read_item(
    item_id: UUID,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WardrobeItemResponse:
    return get_wardrobe_item(item_id, session, user)
