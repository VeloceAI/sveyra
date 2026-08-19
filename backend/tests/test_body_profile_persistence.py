from uuid import uuid4

from fastapi.testclient import TestClient

from tests.auth_helpers import register_and_auth

BODY_PAYLOAD = {
    "measurements": {"notes": "standing relaxed"},
    "fit_preferences": {"ease": "regular"},
}


def test_post_body_profile_persists_measurements_and_fit(client: TestClient) -> None:
    user_id, headers = register_and_auth(client, "body-user@example.com")
    response = client.post(f"/v1/profile/{user_id}/body", json=BODY_PAYLOAD, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == user_id
    assert body["measurements"] == {"notes": "standing relaxed"}
    assert body["fit_preferences"] == {"ease": "regular"}
    assert body["id"]


def test_get_body_profile_returns_persisted_rows(client: TestClient) -> None:
    user_id, headers = register_and_auth(client, "body-user@example.com")
    created = client.post(
        f"/v1/profile/{user_id}/body", json=BODY_PAYLOAD, headers=headers
    ).json()
    response = client.get(f"/v1/profile/{user_id}/body", headers=headers)
    assert response.status_code == 200
    body = response.json()
    profiles = body["body_profiles"]
    assert body["total"] == 1
    assert body["limit"] == 50
    assert body["offset"] == 0
    assert len(profiles) == 1
    assert profiles[0]["id"] == created["id"]
    assert profiles[0]["measurements"] == {"notes": "standing relaxed"}
    assert profiles[0]["fit_preferences"] == {"ease": "regular"}


def test_post_body_profile_appends_another_row(client: TestClient) -> None:
    user_id, headers = register_and_auth(client, "body-user@example.com")
    first = client.post(
        f"/v1/profile/{user_id}/body", json=BODY_PAYLOAD, headers=headers
    ).json()
    second_payload = {
        "measurements": {"notes": "updated stance"},
        "fit_preferences": {"ease": "relaxed"},
    }
    second = client.post(
        f"/v1/profile/{user_id}/body", json=second_payload, headers=headers
    ).json()
    assert first["id"] != second["id"]
    ids = {
        item["id"]
        for item in client.get(f"/v1/profile/{user_id}/body", headers=headers).json()[
            "body_profiles"
        ]
    }
    assert ids == {first["id"], second["id"]}
    listed = client.get(f"/v1/profile/{user_id}/body", headers=headers).json()
    assert listed["total"] == 2


def test_missing_body_profile_returns_404(client: TestClient) -> None:
    user_id, headers = register_and_auth(client, "body-user@example.com")
    response = client.get(f"/v1/profile/{user_id}/body", headers=headers)
    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "body_profile_not_found",
            "message": "Body profile was not found.",
        }
    }


def test_body_path_for_another_user_is_rejected(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "body-user@example.com")
    missing = uuid4()
    response = client.post(f"/v1/profile/{missing}/body", json=BODY_PAYLOAD, headers=headers)
    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "user_not_found",
            "message": "User was not found.",
        }
    }
