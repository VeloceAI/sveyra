from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.handlers.auth_handler import login_user, register_user
from app.schemas.auth_schema import LoginRequest, RegisterRequest, RegisterResponse, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])

_auth_rate_limit = Depends(rate_limit("auth_limiter"))


@router.post("/register", response_model=RegisterResponse, dependencies=[_auth_rate_limit])
def register(payload: RegisterRequest, session: Session = Depends(get_db)) -> RegisterResponse:
    return register_user(payload, session)


@router.post("/login", response_model=TokenResponse, dependencies=[_auth_rate_limit])
def login(payload: LoginRequest, session: Session = Depends(get_db)) -> TokenResponse:
    return login_user(payload, session)
