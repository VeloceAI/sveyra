from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.tokens import parse_access_token
from app.core.errors import InvalidTokenError, UnauthorizedError
from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import AuthService

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise UnauthorizedError
    user_id = parse_access_token(credentials.credentials)
    user = AuthService().get_user(session, user_id)
    if user is None:
        raise InvalidTokenError
    return user
