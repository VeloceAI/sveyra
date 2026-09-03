import pytest
from fastapi.testclient import TestClient

from app.core.errors import RateLimitExceededError
from app.core.rate_limit import SlidingWindowRateLimiter


def test_login_is_rate_limited_after_repeated_attempts(client: TestClient) -> None:
    client.app.state.auth_limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=60)
    payload = {"email": "brute@example.com", "password": "not-the-password"}

    statuses = [client.post("/v1/auth/login", json=payload).status_code for _ in range(4)]

    assert statuses[:3] == [401, 401, 401]
    assert statuses[3] == 429


def test_rate_limited_response_uses_the_error_envelope(client: TestClient) -> None:
    client.app.state.auth_limiter = SlidingWindowRateLimiter(max_requests=1, window_seconds=60)
    payload = {"email": "envelope@example.com", "password": "not-the-password"}

    client.post("/v1/auth/login", json=payload)
    blocked = client.post("/v1/auth/login", json=payload)

    assert blocked.status_code == 429
    assert blocked.json() == {
        "error": {
            "code": "rate_limit_exceeded",
            "message": "Too many requests. Wait a moment and try again.",
        }
    }


def test_register_shares_the_same_limiter(client: TestClient) -> None:
    client.app.state.auth_limiter = SlidingWindowRateLimiter(max_requests=1, window_seconds=60)

    client.post("/v1/auth/login", json={"email": "a@example.com", "password": "password123"})
    blocked = client.post(
        "/v1/auth/register", json={"email": "b@example.com", "password": "password123"}
    )

    assert blocked.status_code == 429


def test_limiter_allows_traffic_again_once_the_window_passes() -> None:
    limiter = SlidingWindowRateLimiter(max_requests=1, window_seconds=0)
    limiter.check("caller")
    limiter.check("caller")


def test_limiter_counts_each_caller_separately() -> None:
    limiter = SlidingWindowRateLimiter(max_requests=1, window_seconds=60)
    limiter.check("caller-a")
    limiter.check("caller-b")
    with pytest.raises(RateLimitExceededError):
        limiter.check("caller-a")
