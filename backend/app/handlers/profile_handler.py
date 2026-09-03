from uuid import UUID

from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.persist_schema import PersistedProfileResponse, ProfilePersistRequest
from app.schemas.profile_schema import ProfileSummary
from app.services.profile_service import ProfileService


def get_profile_summary() -> ProfileSummary:
    service = ProfileService()
    return service.get_summary()


def persist_profile(
    payload: ProfilePersistRequest, session: Session, user: User
) -> PersistedProfileResponse:
    service = ProfileService()
    return service.persist_profile(session, user.id, payload)


def get_persisted_profile(
    user_id: UUID, session: Session, user: User
) -> PersistedProfileResponse:
    service = ProfileService()
    return service.get_persisted_profile(session, user_id, user.id)
