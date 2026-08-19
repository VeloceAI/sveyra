from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from app.core.config import settings
from app.core.errors import InvalidTokenError

ALGORITHM = "HS256"


def create_access_token(user_id: UUID) -> str:
    expires = datetime.now(UTC) + timedelta(seconds=settings.jwt_access_ttl_seconds)
    payload = {"sub": str(user_id), "exp": expires}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def parse_access_token(token: str) -> UUID:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise InvalidTokenError
    subject = payload.get("sub")
    if not isinstance(subject, str):
        raise InvalidTokenError
    try:
        return UUID(subject)
    except ValueError:
        raise InvalidTokenError
