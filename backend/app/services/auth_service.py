from uuid import UUID

from sqlalchemy.orm import Session

from app.auth.passwords import hash_password, verify_password
from app.auth.tokens import create_access_token
from app.core.errors import EmailAlreadyRegisteredError, InvalidCredentialsError
from app.models.user import User
from app.repositories.auth_repository import AuthRepository
from app.schemas.auth_schema import LoginRequest, RegisterRequest, RegisterResponse, TokenResponse


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
        return TokenResponse(access_token=create_access_token(user.id))

    def get_user(self, session: Session, user_id: UUID) -> User | None:
        return self.repository.get_user_by_id(session, user_id)
