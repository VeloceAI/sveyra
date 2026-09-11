from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from fastapi.testclient import TestClient

from app.core.config import settings
from tests.auth_helpers import TEST_PASSWORD, register_and_auth

UNAUTHORIZED = {
    "error": {"code": "unauthorized", "message": "Authentication is required."}
}
INVALID_TOKEN = {
    "error": {"code": "invalid_token", "message": "The access token is invalid."}
}
INVALID_CREDENTIALS = {
    "error": {"code": "invalid_credentials", "message": "Email or password is incorrect."}
}


def test_register_success(client: TestClient) -> None:
    response = client.post(
        "/v1/auth/register",
        json={"email": "ada@example.com", "password": TEST_PASSWORD},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "ada@example.com"
    assert body["id"]
    assert "password" not in body
    assert "password_hash" not in body


def test_register_duplicate_email(client: TestClient) -> None:
    payload = {"email": "ada@example.com", "password": TEST_PASSWORD}
    assert client.post("/v1/auth/register", json=payload).status_code == 200
    response = client.post("/v1/auth/register", json=payload)
    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "email_already_registered",
            "message": "Email is already registered.",
        }
    }


def test_login_success(client: TestClient) -> None:
    client.post(
        "/v1/auth/register",
        json={"email": "ada@example.com", "password": TEST_PASSWORD},
    )
    response = client.post(
        "/v1/auth/login",
        json={"email": "ada@example.com", "password": TEST_PASSWORD},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert "password" not in body


def test_local_development_session_skips_the_login_screen_with_real_tokens(
    client: TestClient, monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "enable_dev_session", True)
    response = client.post("/v1/auth/dev-session", json={})

    assert response.status_code == 200
    tokens = response.json()
    assert tokens["access_token"]
    protected = client.get(
        "/v1/wardrobe",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert protected.status_code == 200


def test_development_session_is_closed_unless_explicitly_enabled(
    client: TestClient,
) -> None:
    """The default must be closed, with nothing set either way.

    Gating this on app_env alone was fail-open: app_env defaults to "local", so
    a deployment that forgot to set APP_ENV kept an unauthenticated
    token-minting endpoint live.
    """
    assert settings.enable_dev_session is False
    response = client.post("/v1/auth/dev-session", json={})
    assert response.status_code == 404


def test_development_session_is_not_exposed_in_production(
    client: TestClient, monkeypatch,
) -> None:
    """Even with the flag on, a non-local APP_ENV closes it."""
    monkeypatch.setattr(settings, "enable_dev_session", True)
    monkeypatch.setattr(settings, "app_env", "production")
    response = client.post("/v1/auth/dev-session", json={})
    assert response.status_code == 404


def test_login_wrong_password(client: TestClient) -> None:
    client.post(
        "/v1/auth/register",
        json={"email": "ada@example.com", "password": TEST_PASSWORD},
    )
    response = client.post(
        "/v1/auth/login",
        json={"email": "ada@example.com", "password": "wrongpass"},
    )
    assert response.status_code == 401
    assert response.json() == INVALID_CREDENTIALS


def test_login_unknown_email_uses_same_envelope(client: TestClient) -> None:
    response = client.post(
        "/v1/auth/login",
        json={"email": "missing@example.com", "password": TEST_PASSWORD},
    )
    assert response.status_code == 401
    assert response.json() == INVALID_CREDENTIALS


def test_protected_route_missing_authorization(client: TestClient) -> None:
    response = client.get("/v1/wardrobe")
    assert response.status_code == 401
    assert response.json() == UNAUTHORIZED


def test_protected_route_malformed_bearer_token(client: TestClient) -> None:
    response = client.get("/v1/wardrobe", headers={"Authorization": "Bearer not-a-jwt"})
    assert response.status_code == 401
    assert response.json() == INVALID_TOKEN


def test_expired_jwt_is_rejected(client: TestClient) -> None:
    user_id, _ = register_and_auth(client, "expired@example.com")
    token = jwt.encode(
        {"sub": user_id, "exp": datetime.now(UTC) - timedelta(seconds=30)},
        settings.jwt_secret,
        algorithm="HS256",
    )
    response = client.get("/v1/wardrobe", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json() == INVALID_TOKEN


def test_invalid_jwt_signature_is_rejected(client: TestClient) -> None:
    user_id, _ = register_and_auth(client, "sig@example.com")
    token = jwt.encode(
        {"sub": user_id, "exp": datetime.now(UTC) + timedelta(seconds=900)},
        "other-secret",
        algorithm="HS256",
    )
    response = client.get("/v1/wardrobe", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json() == INVALID_TOKEN


def test_invalid_jwt_subject_is_rejected(client: TestClient) -> None:
    token = jwt.encode(
        {"sub": "not-a-uuid", "exp": datetime.now(UTC) + timedelta(seconds=900)},
        settings.jwt_secret,
        algorithm="HS256",
    )
    response = client.get("/v1/wardrobe", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json() == INVALID_TOKEN


def test_nonexistent_jwt_subject_is_rejected(client: TestClient) -> None:
    token = jwt.encode(
        {"sub": str(uuid4()), "exp": datetime.now(UTC) + timedelta(seconds=900)},
        settings.jwt_secret,
        algorithm="HS256",
    )
    response = client.get("/v1/wardrobe", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json() == INVALID_TOKEN


def test_client_supplied_user_id_cannot_impersonate(client: TestClient) -> None:
    user_a, headers_a = register_and_auth(client, "impersonate-a@example.com")
    user_b, _headers_b = register_and_auth(client, "impersonate-b@example.com")
    rejected = client.post(
        "/v1/wardrobe",
        headers=headers_a,
        json={
            "user_id": user_b,
            "category": "shirt",
            "color": "navy",
            "brand": "unbranded",
            "attributes": {},
        },
    )
    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "validation_error"

    created = client.post(
        "/v1/wardrobe",
        headers=headers_a,
        json={
            "category": "shirt",
            "color": "navy",
            "brand": "unbranded",
            "attributes": {},
        },
    )
    assert created.status_code == 200
    assert created.json()["user_id"] == user_a
    assert created.json()["user_id"] != user_b


def test_health_remains_public(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
