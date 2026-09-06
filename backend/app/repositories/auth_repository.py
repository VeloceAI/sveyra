from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.refresh_token import RefreshToken
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

    def create_refresh_token(
        self, session: Session, user_id: UUID, token_hash: str, expires_at: datetime
    ) -> RefreshToken:
        token = RefreshToken(
            id=uuid4(),
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        session.add(token)
        return token

    def get_refresh_token_by_hash(self, session: Session, token_hash: str) -> RefreshToken | None:
        return session.scalars(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        ).first()

    def revoke_refresh_token(self, session: Session, token: RefreshToken) -> None:
        token.revoked_at = datetime.now(UTC)

    def revoke_all_for_user(self, session: Session, user_id: UUID) -> None:
        session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
