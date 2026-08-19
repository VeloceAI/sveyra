from uuid import uuid4

from fastapi.testclient import TestClient

from app.storage.deps import get_storage
from app.storage.errors import StorageUnavailableError
from app.storage.memory import InMemoryStorage
from tests.auth_helpers import register_and_auth

UPLOAD_BYTES = b"example image bytes"


def _upload(client: TestClient, headers: dict[str, str], payload: bytes = UPLOAD_BYTES):
    return client.post(
        "/v1/media/upload",
        headers=headers,
        files={"file": ("garment.jpg", payload, "image/jpeg")},
    )


class UnavailableStorage(InMemoryStorage):
    def create_access_url(self, reference: str, expires_seconds: int) -> str:
        raise StorageUnavailableError


def test_access_returns_temporary_url(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "access-user@example.com")
    upload_response = _upload(client, headers)
    asset_id = upload_response.json()["id"]
    reference = upload_response.json()["reference"]

    response = client.get(f"/v1/media/{asset_id}/access", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body == {"url": f"memory://{reference}"}


def test_access_missing_asset_returns_not_found(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "access-user@example.com")
    response = client.get(f"/v1/media/{uuid4()}/access", headers=headers)
    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "media_asset_not_found", "message": "Media asset was not found."}
    }


def test_cannot_access_another_users_media(client: TestClient) -> None:
    _user_a, headers_a = register_and_auth(client, "access-a@example.com")
    _user_b, headers_b = register_and_auth(client, "access-b@example.com")
    asset_id = _upload(client, headers_a).json()["id"]
    response = client.get(f"/v1/media/{asset_id}/access", headers=headers_b)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "media_asset_not_found"


def test_access_storage_failure_returns_unavailable(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "access-user@example.com")
    asset_id = _upload(client, headers).json()["id"]
    client.app.dependency_overrides[get_storage] = lambda: UnavailableStorage()

    response = client.get(f"/v1/media/{asset_id}/access", headers=headers)
    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "storage_unavailable",
            "message": "Media storage is temporarily unavailable.",
        }
    }
    client.app.dependency_overrides.pop(get_storage, None)


def test_access_does_not_modify_reference(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "access-user@example.com")
    upload_body = _upload(client, headers).json()
    asset_id = upload_body["id"]
    original_reference = upload_body["reference"]

    client.get(f"/v1/media/{asset_id}/access", headers=headers)

    metadata = client.get(f"/v1/media/{asset_id}", headers=headers).json()
    assert metadata["reference"] == original_reference
    assert metadata["reference"] == upload_body["reference"]
    assert "://" not in metadata["reference"]


def test_metadata_get_still_returns_metadata_only(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "access-user@example.com")
    upload_body = _upload(client, headers).json()
    asset_id = upload_body["id"]

    response = client.get(f"/v1/media/{asset_id}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"id", "user_id", "wardrobe_item_id", "reference"}
    assert body["id"] == asset_id
    assert "url" not in body


def test_upload_still_works_after_access_endpoint(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "access-user@example.com")
    response = _upload(client, headers)
    assert response.status_code == 200
    assert response.json()["reference"].startswith("asset_")
