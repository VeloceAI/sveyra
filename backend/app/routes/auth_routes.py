from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.handlers.auth_handler import (
    create_development_session,
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

_auth_rate_limit = Depends(rate_limit("auth_limiter"))
_LOCAL_ENVS = frozenset({"local", "dev", "development", "test"})


@router.post("/dev-session", response_model=TokenResponse, dependencies=[_auth_rate_limit])
def development_session(session: Session = Depends(get_db)) -> TokenResponse:
    """Skip the login screen locally while still exercising real JWT auth.

    Needs both an explicit ENABLE_DEV_SESSION and a local APP_ENV. The flag is
    what makes it safe: a deployment that sets neither gets nothing, where
    relying on APP_ENV alone meant forgetting one variable was enough to leave
    this open.
    """
    if not settings.enable_dev_session:
        raise HTTPException(status_code=404, detail="Not found")
    if settings.app_env.strip().lower() not in _LOCAL_ENVS:
        raise HTTPException(status_code=404, detail="Not found")
    return create_development_session(session)


@router.post("/register", response_model=RegisterResponse, dependencies=[_auth_rate_limit])
def register(payload: RegisterRequest, session: Session = Depends(get_db)) -> RegisterResponse:
    return register_user(payload, session)


@router.post("/login", response_model=TokenResponse, dependencies=[_auth_rate_limit])
def login(payload: LoginRequest, session: Session = Depends(get_db)) -> TokenResponse:
    return login_user(payload, session)


@router.post("/refresh", response_model=TokenResponse, dependencies=[_auth_rate_limit])
def refresh(payload: RefreshRequest, session: Session = Depends(get_db)) -> TokenResponse:
    return refresh_tokens(payload, session)


@router.post("/logout", status_code=204)
def logout(payload: RefreshRequest, session: Session = Depends(get_db)) -> None:
    logout_user(payload, session)
