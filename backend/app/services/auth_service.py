from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.auth.passwords import hash_password, verify_password
from app.auth.tokens import (
    create_access_token,
    create_refresh_token,
    hash_refresh_token,
    refresh_token_expiry,
)
from app.core.errors import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
)
from app.models.user import User
from app.repositories.auth_repository import AuthRepository
from app.schemas.auth_schema import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)


def _as_utc(value: datetime) -> datetime:
    # SQLite hands back naive datetimes even for timezone-aware columns.
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


class AuthService:
    def __init__(self, repository: AuthRepository | None = None) -> None:
        self.repository = repository or AuthRepository()

    def register(self, session: Session, payload: RegisterRequest) -> RegisterResponse:
        email = payload.email.strip().lower()
        if self.repository.get_user_by_email(session, email) is not None:
            raise EmailAlreadyRegisteredError
        user = self.repository.create_user(session, email, hash_password(payload.password))
        session.commit()
        session.refresh(user)
        return RegisterResponse(id=user.id, email=user.email)

    def login(self, session: Session, payload: LoginRequest) -> TokenResponse:
        email = payload.email.strip().lower()
        user = self.repository.get_user_by_email(session, email)
        if user is None or not verify_password(payload.password, user.password_hash):
            raise InvalidCredentialsError
        return self._issue_tokens(session, user.id)

    def refresh(self, session: Session, payload: RefreshRequest) -> TokenResponse:
        stored = self.repository.get_refresh_token_by_hash(
            session, hash_refresh_token(payload.refresh_token)
        )
        if stored is None:
            raise InvalidRefreshTokenError
        if stored.revoked_at is not None:
            # A revoked token was replayed. Tokens rotate on every use, so the
            # only way this happens is that someone kept a copy: drop the whole
            # session family rather than trust either holder.
            self.repository.revoke_all_for_user(session, stored.user_id)
            session.commit()
            raise InvalidRefreshTokenError
        if _as_utc(stored.expires_at) <= datetime.now(UTC):
            raise InvalidRefreshTokenError

        self.repository.revoke_refresh_token(session, stored)
        return self._issue_tokens(session, stored.user_id)

    def logout(self, session: Session, payload: RefreshRequest) -> None:
        stored = self.repository.get_refresh_token_by_hash(
            session, hash_refresh_token(payload.refresh_token)
        )
        # Logout is idempotent: an unknown or already-revoked token still ends
        # with the caller logged out, and saying which it was leaks nothing.
        if stored is not None and stored.revoked_at is None:
            self.repository.revoke_refresh_token(session, stored)
        session.commit()

    def revoke_all_sessions(self, session: Session, user_id: UUID) -> None:
        self.repository.revoke_all_for_user(session, user_id)
        session.commit()

    def get_user(self, session: Session, user_id: UUID) -> User | None:
        return self.repository.get_user_by_id(session, user_id)

    def _issue_tokens(self, session: Session, user_id: UUID) -> TokenResponse:
        refresh = create_refresh_token()
        self.repository.create_refresh_token(
            session, user_id, hash_refresh_token(refresh), refresh_token_expiry()
        )
        session.commit()
        return TokenResponse(
            access_token=create_access_token(user_id),
            refresh_token=refresh,
        )
