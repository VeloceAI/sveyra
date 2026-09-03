from sqlalchemy.orm import Session

from app.schemas.auth_schema import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)
from app.services.auth_service import AuthService


def register_user(payload: RegisterRequest, session: Session) -> RegisterResponse:
    return AuthService().register(session, payload)


def login_user(payload: LoginRequest, session: Session) -> TokenResponse:
    return AuthService().login(session, payload)


def refresh_tokens(payload: RefreshRequest, session: Session) -> TokenResponse:
    return AuthService().refresh(session, payload)


def logout_user(payload: RefreshRequest, session: Session) -> None:
    AuthService().logout(session, payload)
