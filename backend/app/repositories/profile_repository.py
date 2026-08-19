from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.style_profile import StyleProfile
from app.models.user import User


class ProfileRepository:
    def get_demo_profile(self) -> dict[str, object]:
        return {
            "user_id": "demo",
            "style_words": ["minimal", "sharp", "comfortable"],
            "wardrobe_items": 0,
            "fit_profile_ready": False,
            "avatar_ready": False,
        }

    def get_user_by_email(self, session: Session, email: str) -> User | None:
        return session.scalars(select(User).where(User.email == email)).first()

    def get_user_by_id(self, session: Session, user_id: UUID) -> User | None:
        return session.get(User, user_id)

    def create_user(self, session: Session, email: str, password_hash: str) -> User:
        user = User(id=uuid4(), email=email, password_hash=password_hash)
        session.add(user)
        return user

    def get_style_profile_by_user_id(
        self, session: Session, user_id: UUID
    ) -> StyleProfile | None:
        return session.scalars(
            select(StyleProfile).where(StyleProfile.user_id == user_id)
        ).first()

    def create_style_profile(
        self,
        session: Session,
        user_id: UUID,
        preferences: dict[str, object],
        dislikes: dict[str, object],
        budget: dict[str, object],
    ) -> StyleProfile:
        profile = StyleProfile(
            id=uuid4(),
            user_id=user_id,
            preferences=preferences,
            dislikes=dislikes,
            budget=budget,
        )
        session.add(profile)
        return profile
