from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db.session import get_db
from app.handlers.profile_handler import (
    get_persisted_profile,
    get_profile_summary,
    persist_profile,
)
from app.models.user import User
from app.schemas.persist_schema import PersistedProfileResponse, ProfilePersistRequest
from app.schemas.profile_schema import ProfileSummary

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/summary", response_model=ProfileSummary)
def profile_summary() -> ProfileSummary:
    return get_profile_summary()


@router.post("", response_model=PersistedProfileResponse)
def create_profile(
    payload: ProfilePersistRequest,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PersistedProfileResponse:
    return persist_profile(payload, session, user)


@router.get("", response_model=PersistedProfileResponse)
def read_current_profile(
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PersistedProfileResponse:
    return get_persisted_profile(user.id, session, user)


@router.get("/{user_id}", response_model=PersistedProfileResponse)
def read_profile(
    user_id: UUID,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PersistedProfileResponse:
    return get_persisted_profile(user_id, session, user)
