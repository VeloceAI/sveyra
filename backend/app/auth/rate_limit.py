from collections import defaultdict
from threading import Lock
from time import monotonic

from fastapi import Request

from app.core.config import settings
from app.core.errors import AuthRateLimitExceededError

_lock = Lock()
_attempts: dict[str, list[float]] = defaultdict(list)


def reset_auth_rate_limiter() -> None:
    with _lock:
        _attempts.clear()


def _client_key(request: Request) -> str:
    if request.client is None:
        return "unknown"
    return request.client.host


def enforce_auth_rate_limit(request: Request, scope: str) -> None:
    max_attempts = settings.auth_rate_limit_max_attempts
    if max_attempts <= 0:
        return

    key = f"{scope}:{_client_key(request)}"
    now = monotonic()
    window = settings.auth_rate_limit_window_seconds

    with _lock:
        timestamps = [timestamp for timestamp in _attempts[key] if timestamp > now - window]
        if len(timestamps) >= max_attempts:
            raise AuthRateLimitExceededError
        timestamps.append(now)
        _attempts[key] = timestamps


def login_rate_limit(request: Request) -> None:
    enforce_auth_rate_limit(request, "login")


def register_rate_limit(request: Request) -> None:
    enforce_auth_rate_limit(request, "register")
