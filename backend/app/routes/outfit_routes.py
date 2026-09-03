from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db.session import get_db
from app.handlers.outfit_handler import create_outfit, get_outfit, list_outfits
from app.models.user import User
from app.schemas.common import DEFAULT_LIST_LIMIT, MAX_LIST_LIMIT
from app.schemas.outfit_schema import OutfitCreateRequest, OutfitListResponse, OutfitResponse

router = APIRouter(prefix="/outfits", tags=["outfits"])


@router.post("", response_model=OutfitResponse)
def create_item(
    payload: OutfitCreateRequest,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OutfitResponse:
    return create_outfit(payload, session, user)


@router.get("", response_model=OutfitListResponse)
def list_items(
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = Query(default=DEFAULT_LIST_LIMIT, ge=1, le=MAX_LIST_LIMIT),
    offset: int = Query(default=0, ge=0),
) -> OutfitListResponse:
    return list_outfits(session, user, limit=limit, offset=offset)


@router.get("/{outfit_id}", response_model=OutfitResponse)
def read_item(
    outfit_id: UUID,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OutfitResponse:
    return get_outfit(outfit_id, session, user)
