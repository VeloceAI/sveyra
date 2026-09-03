from uuid import uuid4

from fastapi.testclient import TestClient

from tests.auth_helpers import TEST_PASSWORD, register_and_auth


def test_malformed_uuid_returns_validation_envelope(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "uuid-user@example.com")
    response = client.get("/v1/wardrobe/not-a-uuid", headers=headers)
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert "traceback" not in str(body).lower()
    assert "sql" not in str(body).lower()


def test_missing_required_wardrobe_fields_rejected(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "missing-fields@example.com")
    response = client.post("/v1/wardrobe", headers=headers, json={"category": "shirt"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_empty_string_fields_rejected(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "empty-string@example.com")
    response = client.post(
        "/v1/wardrobe",
        headers=headers,
        json={"category": "", "color": "navy", "brand": "x", "attributes": {}},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_invalid_email_rejected(client: TestClient) -> None:
    response = client.post(
        "/v1/auth/register",
        json={"email": "not-an-email", "password": TEST_PASSWORD},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_unexpected_request_fields_rejected(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "extra-fields@example.com")
    response = client.post(
        "/v1/wardrobe",
        headers=headers,
        json={
            "category": "shirt",
            "color": "navy",
            "brand": "unbranded",
            "attributes": {},
            "unexpected": "nope",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_wardrobe_list_pagination_bounds(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "page-user@example.com")
    for index in range(3):
        client.post(
            "/v1/wardrobe",
            headers=headers,
            json={
                "category": f"cat-{index}",
                "color": "navy",
                "brand": "unbranded",
                "attributes": {},
            },
        )

    page = client.get("/v1/wardrobe", headers=headers, params={"limit": 2, "offset": 1})
    assert page.status_code == 200
    body = page.json()
    assert body["limit"] == 2
    assert body["offset"] == 1
    assert body["total"] == 3
    assert len(body["wardrobe_items"]) == 2

    too_large = client.get("/v1/wardrobe", headers=headers, params={"limit": 101})
    assert too_large.status_code == 422
    assert too_large.json()["error"]["code"] == "validation_error"

    negative = client.get("/v1/wardrobe", headers=headers, params={"offset": -1})
    assert negative.status_code == 422
    assert negative.json()["error"]["code"] == "validation_error"

    zero_limit = client.get("/v1/wardrobe", headers=headers, params={"limit": 0})
    assert zero_limit.status_code == 422
    assert zero_limit.json()["error"]["code"] == "validation_error"


def test_outfit_list_pagination_defaults(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "outfit-page@example.com")
    client.post("/v1/outfits", headers=headers, json={"occasion": "casual", "item_ids": []})
    response = client.get("/v1/outfits", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["limit"] == 50
    assert body["offset"] == 0
    assert body["total"] == 1
    assert len(body["outfits"]) == 1


def test_media_reference_empty_rejected(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "media-ref@example.com")
    response = client.post("/v1/media", headers=headers, json={"reference": ""})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_validation_errors_do_not_leak_internals(client: TestClient) -> None:
    response = client.post(
        "/v1/auth/login",
        json={"email": "bad", "password": "short"},
    )
    assert response.status_code == 422
    payload = response.json()
    assert set(payload.keys()) == {"error"}
    assert set(payload["error"].keys()) == {"code", "message"}
    message = payload["error"]["message"].lower()
    assert "traceback" not in message
    assert "sqlalchemy" not in message
    assert "google" not in message
    assert "jwt" not in message


def test_cross_user_media_access_still_blocked(client: TestClient) -> None:
    _user_a, headers_a = register_and_auth(client, "harden-a@example.com")
    _user_b, headers_b = register_and_auth(client, "harden-b@example.com")
    created = client.post(
        "/v1/media/upload",
        headers=headers_a,
        files={"file": ("garment.jpg", b"bytes", "image/jpeg")},
    ).json()
    asset_id = created["id"]
    assert client.get(f"/v1/media/{asset_id}", headers=headers_b).status_code == 404
    assert client.get(f"/v1/media/{asset_id}/access", headers=headers_b).status_code == 404
    assert client.delete(f"/v1/media/{asset_id}", headers=headers_b).status_code == 404
    assert client.get(f"/v1/media/{asset_id}", headers=headers_a).status_code == 200


def test_unauthorized_list_still_401(client: TestClient) -> None:
    response = client.get("/v1/wardrobe")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_body_profile_path_user_mismatch_rejected(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "body-harden@example.com")
    response = client.post(
        f"/v1/profile/{uuid4()}/body",
        headers=headers,
        json={"measurements": {}, "fit_preferences": {}},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "user_not_found"
