from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class AuthRepository:
    def get_user_by_email(self, session: Session, email: str) -> User | None:
        return session.scalars(select(User).where(User.email == email)).first()

    def get_user_by_id(self, session: Session, user_id: UUID) -> User | None:
        return session.get(User, user_id)

    def create_user(self, session: Session, email: str, password_hash: str) -> User:
        user = User(id=uuid4(), email=email, password_hash=password_hash)
        session.add(user)
        return user
