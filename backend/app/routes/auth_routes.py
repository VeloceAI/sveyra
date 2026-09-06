from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.rate_limit import login_rate_limit, register_rate_limit
from app.db.session import get_db
from app.handlers.auth_handler import (
    login_user,
    logout_user,
    refresh_tokens,
    register_user,
)
from app.schemas.auth_schema import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse)
def register(
    payload: RegisterRequest,
    session: Session = Depends(get_db),
    _: None = Depends(register_rate_limit),
) -> RegisterResponse:
    return register_user(payload, session)


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    session: Session = Depends(get_db),
    _: None = Depends(login_rate_limit),
) -> TokenResponse:
    return login_user(payload, session)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    payload: RefreshRequest,
    session: Session = Depends(get_db),
) -> TokenResponse:
    return refresh_tokens(payload, session)


@router.post("/logout", status_code=204)
def logout(
    payload: RefreshRequest,
    session: Session = Depends(get_db),
) -> None:
    logout_user(payload, session)