from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.appearance_schema import (
    AppearanceProfilePersistRequest,
    AppearanceProfileResponse,
)
from app.services.appearance_service import AppearanceService


def upsert_appearance(
    payload: AppearanceProfilePersistRequest,
    session: Session,
    user: User,
) -> AppearanceProfileResponse:
    return AppearanceService().upsert(session, user.id, payload)


def get_appearance(session: Session, user: User) -> AppearanceProfileResponse:
    return AppearanceService().get(session, user.id)
