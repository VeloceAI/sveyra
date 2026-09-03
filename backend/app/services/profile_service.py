from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import ProfileNotFoundError
from app.models.style_profile import StyleProfile
from app.models.user import User
from app.repositories.profile_repository import ProfileRepository
from app.schemas.persist_schema import PersistedProfileResponse, ProfilePersistRequest
from app.schemas.profile_schema import ProfileSummary


class ProfileService:
    def __init__(self, repository: ProfileRepository | None = None) -> None:
        self.repository = repository or ProfileRepository()

    def get_summary(self) -> ProfileSummary:
        profile = self.repository.get_demo_profile()
        return ProfileSummary(**profile)

    def persist_profile(
        self, session: Session, user_id: UUID, payload: ProfilePersistRequest
    ) -> PersistedProfileResponse:
        user = self.repository.get_user_by_id(session, user_id)
        if user is None:
            raise ProfileNotFoundError
        profile = self.repository.get_style_profile_by_user_id(session, user.id)
        if profile is None:
            profile = self.repository.create_style_profile(
                session,
                user.id,
                payload.preferences,
                payload.dislikes,
                payload.budget,
            )
        else:
            profile.preferences = payload.preferences
            profile.dislikes = payload.dislikes
            profile.budget = payload.budget
        session.commit()
        session.refresh(user)
        session.refresh(profile)
        return self._to_response(user, profile)

    def get_persisted_profile(
        self, session: Session, user_id: UUID, owner_id: UUID
    ) -> PersistedProfileResponse:
        if user_id != owner_id:
            raise ProfileNotFoundError
        profile = self.repository.get_style_profile_by_user_id(session, user_id)
        if profile is None:
            raise ProfileNotFoundError
        user = self.repository.get_user_by_id(session, user_id)
        if user is None:
            raise ProfileNotFoundError
        return self._to_response(user, profile)

    def _to_response(self, user: User, profile: StyleProfile) -> PersistedProfileResponse:
        return PersistedProfileResponse(
            user_id=user.id,
            email=user.email,
            style_profile_id=profile.id,
            preferences=profile.preferences,
            dislikes=profile.dislikes,
            budget=profile.budget,
            created_at=user.created_at,
        )
