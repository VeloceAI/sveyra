from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import BodyProfileNotFoundError, UserNotFoundError
from app.models.body_profile import BodyProfile
from app.repositories.body_profile_repository import BodyProfileRepository
from app.schemas.body_profile_schema import (
    BodyProfileListResponse,
    BodyProfilePersistRequest,
    BodyProfileResponse,
)


class BodyProfileService:
    def __init__(self, repository: BodyProfileRepository | None = None) -> None:
        self.repository = repository or BodyProfileRepository()

    def persist_body_profile(
        self, session: Session, user_id: UUID, payload: BodyProfilePersistRequest
    ) -> BodyProfileResponse:
        user = self.repository.get_user_by_id(session, user_id)
        if user is None:
            raise UserNotFoundError
        profile = self.repository.create_body_profile(
            session,
            user_id,
            # exclude_none keeps unset measurements out of the stored JSON rather
            # than writing a null for every field the caller did not send.
            payload.measurements.model_dump(exclude_none=True),
            payload.fit_preferences,
        )
        session.commit()
        session.refresh(profile)
        return self._to_response(profile)

    def list_body_profiles(
        self,
        session: Session,
        user_id: UUID,
        owner_id: UUID,
        *,
        limit: int,
        offset: int,
    ) -> BodyProfileListResponse:
        if user_id != owner_id:
            raise BodyProfileNotFoundError
        user = self.repository.get_user_by_id(session, user_id)
        if user is None:
            raise UserNotFoundError
        profiles, total = self.repository.list_body_profiles_by_user_id(
            session, user_id, limit=limit, offset=offset
        )
        if total == 0:
            raise BodyProfileNotFoundError
        return BodyProfileListResponse(
            body_profiles=[self._to_response(profile) for profile in profiles],
            limit=limit,
            offset=offset,
            total=total,
        )

    def _to_response(self, profile: BodyProfile) -> BodyProfileResponse:
        return BodyProfileResponse(
            id=profile.id,
            user_id=profile.user_id,
            measurements=profile.measurements,
            fit_preferences=profile.fit_preferences,
        )
