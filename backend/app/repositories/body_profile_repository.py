from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.body_profile import BodyProfile
from app.models.user import User


class BodyProfileRepository:
    def get_user_by_id(self, session: Session, user_id: UUID) -> User | None:
        return session.get(User, user_id)

    def list_body_profiles_by_user_id(
        self,
        session: Session,
        user_id: UUID,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[BodyProfile], int]:
        filters = BodyProfile.user_id == user_id
        total = session.scalar(select(func.count()).select_from(BodyProfile).where(filters)) or 0
        profiles = list(
            session.scalars(
                select(BodyProfile).where(filters).offset(offset).limit(limit)
            ).all()
        )
        return profiles, total

    def get_latest_body_profile_by_user_id(
        self, session: Session, user_id: UUID
    ) -> BodyProfile | None:
        # No created_at column yet; append-only rows — use last loaded row as latest.
        profiles = list(
            session.scalars(select(BodyProfile).where(BodyProfile.user_id == user_id)).all()
        )
        return profiles[-1] if profiles else None

    def create_body_profile(
        self,
        session: Session,
        user_id: UUID,
        measurements: dict[str, object],
        fit_preferences: dict[str, object],
    ) -> BodyProfile:
        profile = BodyProfile(
            id=uuid4(),
            user_id=user_id,
            measurements=measurements,
            fit_preferences=fit_preferences,
        )
        session.add(profile)
        return profile
