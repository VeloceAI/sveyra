from uuid import uuid4

from fastapi.testclient import TestClient

from tests.auth_helpers import register_and_auth

UPLOAD_BYTES = b"example image bytes"


def _create_item(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post(
        "/v1/wardrobe",
        headers=headers,
        json={
            "category": "shirt",
            "color": "navy",
            "brand": "unbranded",
            "attributes": {},
        },
    )
    return response.json()["id"]


def _upload(
    client: TestClient,
    headers: dict[str, str],
    payload: bytes = UPLOAD_BYTES,
    wardrobe_item_id: str | None = None,
):
    data: dict[str, str] = {}
    if wardrobe_item_id is not None:
        data["wardrobe_item_id"] = wardrobe_item_id
    return client.post(
        "/v1/media/upload",
        headers=headers,
        data=data,
        files={"file": ("garment.jpg", payload, "image/jpeg")},
    )


def test_upload_media_asset_for_authenticated_user(client: TestClient) -> None:
    user_id, headers = register_and_auth(client, "media-user@example.com")
    response = _upload(client, headers)
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == user_id
    assert body["wardrobe_item_id"] is None
    assert body["id"]
    assert "reference" not in body


def test_upload_media_asset_persists_optional_wardrobe_item_id(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "media-user@example.com")
    item_id = _create_item(client, headers)
    response = _upload(client, headers, wardrobe_item_id=item_id)
    assert response.status_code == 200
    body = response.json()
    assert body["wardrobe_item_id"] == item_id
    assert "reference" not in body


def test_upload_media_asset_rejects_missing_wardrobe_item(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "media-user@example.com")
    response = _upload(client, headers, wardrobe_item_id=str(uuid4()))
    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "wardrobe_item_not_found",
            "message": "Wardrobe item was not found.",
        }
    }


def test_upload_media_asset_rejects_wardrobe_item_owned_by_another_user(
    client: TestClient,
) -> None:
    _user_a, headers_a = register_and_auth(client, "media-a@example.com")
    _user_b, headers_b = register_and_auth(client, "media-b@example.com")
    item_b = _create_item(client, headers_b)
    response = _upload(client, headers_a, wardrobe_item_id=item_b)
    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "wardrobe_item_not_found",
            "message": "Wardrobe item was not found.",
        }
    }


def test_get_existing_media_asset(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "media-user@example.com")
    created = _upload(client, headers).json()
    response = client.get(f"/v1/media/{created['id']}", headers=headers)
    assert response.status_code == 200
    assert response.json() == created
    assert "bytes" not in response.json()
    assert "reference" not in response.json()


def test_cannot_get_another_users_media_asset(client: TestClient) -> None:
    _user_a, headers_a = register_and_auth(client, "media-own@example.com")
    _user_b, headers_b = register_and_auth(client, "media-other@example.com")
    created = _upload(client, headers_a).json()
    response = client.get(f"/v1/media/{created['id']}", headers=headers_b)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "media_asset_not_found"


def test_get_missing_media_asset_returns_error_envelope(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "media-user@example.com")
    response = client.get(f"/v1/media/{uuid4()}", headers=headers)
    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "media_asset_not_found",
            "message": "Media asset was not found.",
        }
    }


def test_multiple_media_assets_can_belong_to_same_wardrobe_item(
    client: TestClient,
) -> None:
    _user_id, headers = register_and_auth(client, "media-user@example.com")
    item_id = _create_item(client, headers)
    first = _upload(client, headers, wardrobe_item_id=item_id)
    second = _upload(client, headers, wardrobe_item_id=item_id)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] != second.json()["id"]
    assert first.json()["wardrobe_item_id"] == item_id
    assert second.json()["wardrobe_item_id"] == item_id


def test_client_supplied_reference_endpoint_removed(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "media-user@example.com")
    response = client.post(
        "/v1/media",
        json={"reference": "user/abc/item/xyz/image-001"},
        headers=headers,
    )
    assert response.status_code == 404
