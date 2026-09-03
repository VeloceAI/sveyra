import hashlib
import secrets
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


def create_refresh_token() -> str:
    """Opaque, high-entropy secret. Not a JWT: validity is a database lookup,
    which is what makes revocation and rotation possible."""
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    # SHA-256 rather than bcrypt: the input is already 384 bits of entropy, so
    # there is nothing for a slow KDF to protect against.
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def refresh_token_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(seconds=settings.refresh_token_ttl_seconds)
