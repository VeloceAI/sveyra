from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.storage.memory import InMemoryStorage
from tests.auth_helpers import register_and_auth

UPLOAD_BYTES = b"example image bytes"
UPLOAD_TOO_LARGE_ERROR = {
    "error": {
        "code": "upload_too_large",
        "message": "Uploaded file exceeds the maximum allowed size.",
    }
}


def _create_item(client: TestClient, headers: dict[str, str]) -> str:
    return client.post(
        "/v1/wardrobe",
        headers=headers,
        json={
            "category": "shirt",
            "color": "navy",
            "brand": "unbranded",
            "attributes": {},
        },
    ).json()["id"]


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


def _opaque_reference_from_storage(client: TestClient, payload: bytes = UPLOAD_BYTES) -> str:
    storage = client.app.state.storage
    assert isinstance(storage, InMemoryStorage)
    for reference, stored in storage._objects.items():
        if stored == payload:
            return reference
    raise AssertionError("storage reference not found for payload")

def test_upload_for_authenticated_user(client: TestClient) -> None:
    user_id, headers = register_and_auth(client, "upload-user@example.com")
    response = _upload(client, headers)
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == user_id
    assert body["wardrobe_item_id"] is None
    assert body["id"]
    assert "reference" not in body


def test_upload_with_wardrobe_item_id(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "upload-user@example.com")
    item_id = _create_item(client, headers)
    response = _upload(client, headers, wardrobe_item_id=item_id)
    assert response.status_code == 200
    assert response.json()["wardrobe_item_id"] == item_id


def test_upload_without_wardrobe_item_id(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "upload-user@example.com")
    body = _upload(client, headers).json()
    assert body["wardrobe_item_id"] is None


def test_upload_form_user_id_cannot_impersonate(client: TestClient) -> None:
    user_a, headers_a = register_and_auth(client, "upload-a@example.com")
    user_b, _headers_b = register_and_auth(client, "upload-b@example.com")
    response = client.post(
        "/v1/media/upload",
        headers=headers_a,
        data={"user_id": user_b},
        files={"file": ("garment.jpg", UPLOAD_BYTES, "image/jpeg")},
    )
    assert response.status_code == 200
    assert response.json()["user_id"] == user_a


def test_upload_rejects_missing_wardrobe_item(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "upload-user@example.com")
    response = _upload(client, headers, wardrobe_item_id=str(uuid4()))
    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "wardrobe_item_not_found",
            "message": "Wardrobe item was not found.",
        }
    }


def test_upload_rejects_foreign_wardrobe_item(client: TestClient) -> None:
    _user_a, headers_a = register_and_auth(client, "upload-own@example.com")
    _user_b, headers_b = register_and_auth(client, "upload-other@example.com")
    item_b = _create_item(client, headers_b)
    response = _upload(client, headers_a, wardrobe_item_id=item_b)
    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "wardrobe_item_not_found",
            "message": "Wardrobe item was not found.",
        }
    }


def test_upload_rejects_empty_file(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "upload-user@example.com")
    response = _upload(client, headers, payload=b"")
    assert response.status_code == 400
    assert response.json() == {
        "error": {"code": "empty_upload", "message": "Uploaded file was empty."}
    }


def test_upload_rejects_oversized_file(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    max_bytes = 1024
    monkeypatch.setattr("app.core.config.settings.media_max_upload_bytes", max_bytes)
    _user_id, headers = register_and_auth(client, "upload-big@example.com")
    response = _upload(client, headers, payload=b"x" * (max_bytes + 1))
    assert response.status_code == 413
    assert response.json() == UPLOAD_TOO_LARGE_ERROR


def test_upload_accepts_file_at_size_limit(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    max_bytes = 1024
    monkeypatch.setattr("app.core.config.settings.media_max_upload_bytes", max_bytes)
    _user_id, headers = register_and_auth(client, "upload-limit@example.com")
    response = _upload(client, headers, payload=b"x" * max_bytes)
    assert response.status_code == 200


def test_upload_persists_metadata_and_bytes_in_storage(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "upload-user@example.com")
    created = _upload(client, headers).json()
    storage = client.app.state.storage
    assert isinstance(storage, InMemoryStorage)
    reference = _opaque_reference_from_storage(client)
    assert storage.get(reference) == UPLOAD_BYTES
    fetched = client.get(f"/v1/media/{created['id']}", headers=headers)
    assert fetched.status_code == 200
    body = fetched.json()
    assert body["id"] == created["id"]
    assert "bytes" not in body
    assert "reference" not in body


def test_client_supplied_reference_endpoint_removed(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "upload-user@example.com")
    response = client.post(
        "/v1/media",
        json={"reference": "user/abc/item/xyz/image-001"},
        headers=headers,
    )
    assert response.status_code == 404
