from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.rate_limit import login_rate_limit, register_rate_limit
from app.db.session import get_db
from app.handlers.auth_handler import login_user, register_user
from app.schemas.auth_schema import (
    LoginRequest,
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