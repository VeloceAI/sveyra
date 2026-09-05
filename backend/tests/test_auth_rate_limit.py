import pytest
from fastapi.testclient import TestClient

from app.core.errors import RateLimitExceededError
from app.core.rate_limit import SlidingWindowRateLimiter
from tests.auth_helpers import TEST_PASSWORD

RATE_LIMIT_ERROR = {
    "error": {
        "code": "rate_limit_exceeded",
        "message": "Too many authentication attempts. Please try again later.",
    }
}


def test_login_succeeds_below_rate_limit(client: TestClient) -> None:
    client.post(
        "/v1/auth/register",
        json={"email": "rate-login@example.com", "password": TEST_PASSWORD},
    )

    response = client.post(
        "/v1/auth/login",
        json={"email": "rate-login@example.com", "password": TEST_PASSWORD},
    )

    assert response.status_code == 200
    assert response.json()["access_token"]


def test_register_succeeds_below_rate_limit(client: TestClient) -> None:
    response = client.post(
        "/v1/auth/register",
        json={
            "email": "rate-register@example.com",
            "password": TEST_PASSWORD,
        },
    )

    assert response.status_code == 200
    assert response.json()["email"] == "rate-register@example.com"


def test_repeated_login_attempts_return_429(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.core.config.settings.auth_rate_limit_window_seconds",
        60,
    )
    monkeypatch.setattr(
        "app.core.config.settings.auth_rate_limit_max_attempts",
        3,
    )

    payload = {
        "email": "hammer-login@example.com",
        "password": TEST_PASSWORD,
    }

    statuses = [
        client.post("/v1/auth/login", json=payload).status_code
        for _ in range(4)
    ]

    assert statuses[:3] == [401, 401, 401]
    assert statuses[3] == 429
    assert client.post(
        "/v1/auth/login",
        json=payload,
    ).json() == RATE_LIMIT_ERROR


def test_repeated_register_attempts_return_429(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.core.config.settings.auth_rate_limit_window_seconds",
        60,
    )
    monkeypatch.setattr(
        "app.core.config.settings.auth_rate_limit_max_attempts",
        2,
    )

    payload = {
        "email": "hammer-register@example.com",
        "password": TEST_PASSWORD,
    }

    statuses = [
        client.post("/v1/auth/register", json=payload).status_code
        for _ in range(3)
    ]

    assert statuses == [200, 409, 429]
    assert client.post(
        "/v1/auth/register",
        json=payload,
    ).json() == RATE_LIMIT_ERROR


def test_limiter_allows_traffic_again_once_the_window_passes() -> None:
    limiter = SlidingWindowRateLimiter(
        max_requests=1,
        window_seconds=0,
    )

    limiter.check("caller")
    limiter.check("caller")


def test_limiter_counts_each_caller_separately() -> None:
    limiter = SlidingWindowRateLimiter(
        max_requests=1,
        window_seconds=60,
    )

    limiter.check("caller-a")
    limiter.check("caller-b")

    with pytest.raises(RateLimitExceededError):
        limiter.check("caller-a")