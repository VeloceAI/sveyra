from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.appearance_profile import AppearanceProfile


class AppearanceRepository:
    def get_by_user_id(
        self,
        session: Session,
        user_id: UUID,
    ) -> AppearanceProfile | None:
        return session.scalars(
            select(AppearanceProfile).where(AppearanceProfile.user_id == user_id)
        ).first()

    def create(
        self,
        session: Session,
        user_id: UUID,
        values: dict[str, dict[str, object]],
    ) -> AppearanceProfile:
        profile = AppearanceProfile(id=uuid4(), user_id=user_id, **values)
        session.add(profile)
        return profile

    def update(
        self,
        profile: AppearanceProfile,
        values: dict[str, dict[str, object]],
    ) -> AppearanceProfile:
        for name, value in values.items():
            setattr(profile, name, value)
        return profile
