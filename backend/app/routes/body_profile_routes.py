from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db.session import get_db
from app.handlers.body_profile_handler import list_body_profiles, persist_body_profile
from app.models.user import User
from app.schemas.body_profile_schema import (
    BodyProfileListResponse,
    BodyProfilePersistRequest,
    BodyProfileResponse,
)
from app.schemas.common import DEFAULT_LIST_LIMIT, MAX_LIST_LIMIT

router = APIRouter(prefix="/profile", tags=["body-profile"])


@router.post("/{user_id}/body", response_model=BodyProfileResponse)
def create_body_profile(
    user_id: UUID,
    payload: BodyProfilePersistRequest,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BodyProfileResponse:
    return persist_body_profile(user_id, payload, session, user)


@router.get("/{user_id}/body", response_model=BodyProfileListResponse)
def read_body_profiles(
    user_id: UUID,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = Query(default=DEFAULT_LIST_LIMIT, ge=1, le=MAX_LIST_LIMIT),
    offset: int = Query(default=0, ge=0),
) -> BodyProfileListResponse:
    return list_body_profiles(user_id, session, user, limit=limit, offset=offset)
