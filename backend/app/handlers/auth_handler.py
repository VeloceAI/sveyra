from sqlalchemy.orm import Session

from app.schemas.auth_schema import LoginRequest, RegisterRequest, RegisterResponse, TokenResponse
from app.services.auth_service import AuthService


def register_user(payload: RegisterRequest, session: Session) -> RegisterResponse:
    return AuthService().register(session, payload)


def login_user(payload: LoginRequest, session: Session) -> TokenResponse:
    return AuthService().login(session, payload)
