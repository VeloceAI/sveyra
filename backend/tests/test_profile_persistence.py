from uuid import uuid4

from fastapi.testclient import TestClient

from tests.auth_helpers import register_and_auth

PROFILE_PAYLOAD = {
    "preferences": {"style": "minimal"},
    "dislikes": {"prints": "loud"},
    "budget": {"currency": "USD", "max": 200},
}


def test_post_profile_uses_authenticated_user(client: TestClient) -> None:
    user_id, headers = register_and_auth(client, "ada@example.com")
    response = client.post("/v1/profile", json=PROFILE_PAYLOAD, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "ada@example.com"
    assert body["preferences"] == {"style": "minimal"}
    assert body["dislikes"] == {"prints": "loud"}
    assert body["budget"] == {"currency": "USD", "max": 200}
    assert body["user_id"] == user_id
    assert body["style_profile_id"]
    assert "created_at" in body
    assert "password" not in body
    assert "password_hash" not in body


def test_get_profile_returns_persisted_profile(client: TestClient) -> None:
    user_id, headers = register_and_auth(client, "ada@example.com")
    created = client.post("/v1/profile", json=PROFILE_PAYLOAD, headers=headers).json()
    response = client.get(f"/v1/profile/{created['user_id']}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == user_id
    assert body["email"] == "ada@example.com"
    assert body["style_profile_id"] == created["style_profile_id"]
    assert body["preferences"] == {"style": "minimal"}
    assert body["dislikes"] == {"prints": "loud"}
    assert body["budget"] == {"currency": "USD", "max": 200}


def test_get_current_profile(client: TestClient) -> None:
    user_id, headers = register_and_auth(client, "ada@example.com")
    created = client.post("/v1/profile", json=PROFILE_PAYLOAD, headers=headers).json()
    response = client.get("/v1/profile", headers=headers)
    assert response.status_code == 200
    assert response.json()["user_id"] == user_id
    assert response.json()["style_profile_id"] == created["style_profile_id"]


def test_missing_profile_returns_documented_404(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "ada@example.com")
    response = client.get(f"/v1/profile/{uuid4()}", headers=headers)
    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "profile_not_found",
            "message": "Profile was not found.",
        }
    }


def test_cannot_read_another_users_profile(client: TestClient) -> None:
    user_a, headers_a = register_and_auth(client, "profile-a@example.com")
    _user_b, headers_b = register_and_auth(client, "profile-b@example.com")
    client.post("/v1/profile", json=PROFILE_PAYLOAD, headers=headers_a)
    response = client.get(f"/v1/profile/{user_a}", headers=headers_b)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "profile_not_found"


def test_repeat_profile_post_stays_on_authenticated_user(client: TestClient) -> None:
    user_id, headers = register_and_auth(client, "ada@example.com")
    first = client.post("/v1/profile", json=PROFILE_PAYLOAD, headers=headers).json()
    second = client.post("/v1/profile", json=PROFILE_PAYLOAD, headers=headers).json()
    assert first["user_id"] == second["user_id"] == user_id
    assert first["style_profile_id"] == second["style_profile_id"]
    fetched = client.get(f"/v1/profile/{first['user_id']}", headers=headers).json()
    assert fetched["user_id"] == first["user_id"]
    assert fetched["style_profile_id"] == first["style_profile_id"]
