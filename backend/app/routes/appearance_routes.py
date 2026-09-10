from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db.session import get_db
from app.handlers.appearance_handler import get_appearance, upsert_appearance
from app.models.user import User
from app.schemas.appearance_schema import (
    AppearanceProfilePersistRequest,
    AppearanceProfileResponse,
)

router = APIRouter(prefix="/appearance", tags=["appearance"])


@router.get("", response_model=AppearanceProfileResponse)
def read_appearance(
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AppearanceProfileResponse:
    return get_appearance(session, user)


@router.put("", response_model=AppearanceProfileResponse)
def save_appearance(
    payload: AppearanceProfilePersistRequest,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AppearanceProfileResponse:
    return upsert_appearance(payload, session, user)
