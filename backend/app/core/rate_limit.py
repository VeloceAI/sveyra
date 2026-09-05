import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import Request

from app.core.errors import RateLimitExceededError


class SlidingWindowRateLimiter:
    """Fixed-capacity sliding window keyed by caller.

    In-process only: with multiple workers the effective limit is per worker.
    Move the counter to Redis before running more than one API process.
    """

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str) -> None:
        now = time.monotonic()
        cutoff = now - self._window_seconds
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if len(hits) >= self._max_requests:
                raise RateLimitExceededError
            hits.append(now)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


def client_key(request: Request) -> str:
    # X-Forwarded-For is only trustworthy behind a proxy that overwrites it.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(limiter_name: str):
    """Build a dependency that consumes one token from a named app-state limiter."""

    def dependency(request: Request) -> None:
        limiter = getattr(request.app.state, limiter_name, None)
        if limiter is None:
            return
        limiter.check(f"{limiter_name}:{client_key(request)}")

    return dependency
