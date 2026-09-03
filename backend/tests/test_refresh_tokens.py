from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker

from app.models.refresh_token import RefreshToken

CREDENTIALS = {"email": "refresh@example.com", "password": "correct-horse-battery"}


def _register_and_login(client: TestClient, email: str = CREDENTIALS["email"]) -> dict[str, str]:
    payload = {"email": email, "password": CREDENTIALS["password"]}
    assert client.post("/v1/auth/register", json=payload).status_code == 200
    response = client.post("/v1/auth/login", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def test_login_returns_an_access_and_refresh_token(client: TestClient) -> None:
    body = _register_and_login(client)
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"


def test_refresh_exchanges_for_a_working_access_token(client: TestClient) -> None:
    tokens = _register_and_login(client)
    refreshed = client.post(
        "/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refreshed.status_code == 200, refreshed.text

    new_access = refreshed.json()["access_token"]
    me = client.get("/v1/wardrobe", headers={"Authorization": f"Bearer {new_access}"})
    assert me.status_code == 200


def test_refresh_rotates_the_token(client: TestClient) -> None:
    tokens = _register_and_login(client)
    refreshed = client.post(
        "/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    ).json()
    assert refreshed["refresh_token"] != tokens["refresh_token"]


def test_a_rotated_token_cannot_be_reused(client: TestClient) -> None:
    tokens = _register_and_login(client)
    client.post("/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    replay = client.post("/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert replay.status_code == 401
    assert replay.json()["error"]["code"] == "invalid_refresh_token"


def test_replaying_an_old_token_kills_the_whole_session_family(client: TestClient) -> None:
    tokens = _register_and_login(client)
    current = client.post(
        "/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    ).json()

    # Replaying the stolen original must invalidate the thief's chain too.
    client.post("/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    after = client.post("/v1/auth/refresh", json={"refresh_token": current["refresh_token"]})
    assert after.status_code == 401


def test_unknown_refresh_token_is_rejected(client: TestClient) -> None:
    _register_and_login(client)
    response = client.post("/v1/auth/refresh", json={"refresh_token": "not-a-real-token"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_refresh_token"


def test_logout_revokes_the_token(client: TestClient) -> None:
    tokens = _register_and_login(client)
    assert (
        client.post("/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]}).status_code
        == 204
    )

    after = client.post("/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert after.status_code == 401


def test_logout_is_idempotent(client: TestClient) -> None:
    tokens = _register_and_login(client)
    first = client.post("/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    second = client.post("/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert first.status_code == 204
    assert second.status_code == 204


def test_logout_with_an_unknown_token_still_succeeds(client: TestClient) -> None:
    _register_and_login(client)
    response = client.post("/v1/auth/logout", json={"refresh_token": "never-issued"})
    assert response.status_code == 204


def test_expired_refresh_token_is_rejected(client: TestClient, sqlite_engine: Engine) -> None:
    tokens = _register_and_login(client)

    factory = sessionmaker(bind=sqlite_engine, expire_on_commit=False)
    with factory() as session:
        stored = session.query(RefreshToken).one()
        stored.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        session.commit()

    response = client.post("/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert response.status_code == 401


def test_the_raw_token_is_never_stored(client: TestClient, sqlite_engine: Engine) -> None:
    tokens = _register_and_login(client)

    factory = sessionmaker(bind=sqlite_engine, expire_on_commit=False)
    with factory() as session:
        stored = session.query(RefreshToken).one()
        assert stored.token_hash != tokens["refresh_token"]
        assert tokens["refresh_token"] not in stored.token_hash


def test_each_user_gets_an_independent_session(client: TestClient) -> None:
    first = _register_and_login(client, "sess-a@example.com")
    second = _register_and_login(client, "sess-b@example.com")

    client.post("/v1/auth/logout", json={"refresh_token": first["refresh_token"]})

    still_valid = client.post(
        "/v1/auth/refresh", json={"refresh_token": second["refresh_token"]}
    )
    assert still_valid.status_code == 200
