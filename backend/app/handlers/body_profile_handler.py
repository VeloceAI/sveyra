from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import BodyProfileNotFoundError, UserNotFoundError
from app.models.user import User
from app.schemas.body_profile_schema import (
    BodyProfileListResponse,
    BodyProfilePersistRequest,
    BodyProfileResponse,
)
from app.schemas.common import DEFAULT_LIST_LIMIT
from app.services.body_profile_service import BodyProfileService


def persist_body_profile(
    user_id: UUID, payload: BodyProfilePersistRequest, session: Session, user: User
) -> BodyProfileResponse:
    if user_id != user.id:
        raise UserNotFoundError
    service = BodyProfileService()
    return service.persist_body_profile(session, user.id, payload)


def list_body_profiles(
    user_id: UUID,
    session: Session,
    user: User,
    *,
    limit: int = DEFAULT_LIST_LIMIT,
    offset: int = 0,
) -> BodyProfileListResponse:
    if user_id != user.id:
        raise BodyProfileNotFoundError
    service = BodyProfileService()
    return service.list_body_profiles(
        session, user.id, user.id, limit=limit, offset=offset
    )
