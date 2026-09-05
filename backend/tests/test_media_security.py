from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.media_asset import MediaAsset
from app.storage.memory import InMemoryStorage
from tests.auth_helpers import register_and_auth

UPLOAD_BYTES = b"user-a garment bytes"


def _upload(client: TestClient, headers: dict[str, str], payload: bytes = UPLOAD_BYTES):
    return client.post(
        "/v1/media/upload",
        headers=headers,
        files={"file": ("garment.jpg", payload, "image/jpeg")},
    )


def test_cross_user_reference_injection_rejected(
    client: TestClient, sqlite_engine
) -> None:
    _user_a, headers_a = register_and_auth(client, "sec-a@example.com")
    _user_b, headers_b = register_and_auth(client, "sec-b@example.com")

    unique_bytes = b"user-a-secret-image"
    upload_a = _upload(client, headers_a, unique_bytes)
    assert upload_a.status_code == 200
    asset_a_id = upload_a.json()["id"]

    with Session(sqlite_engine) as session:
        asset = session.get(MediaAsset, UUID(asset_a_id))
        assert asset is not None
        stolen_reference = asset.reference

    injection = client.post(
        "/v1/media",
        json={"reference": stolen_reference},
        headers=headers_b,
    )
    assert injection.status_code == 404

    assert (
        client.get(f"/v1/media/{asset_a_id}/access", headers=headers_b).status_code == 404
    )
    assert client.delete(f"/v1/media/{asset_a_id}", headers=headers_b).status_code == 404

    access_a = client.get(f"/v1/media/{asset_a_id}/access", headers=headers_a)
    assert access_a.status_code == 200
    storage = client.app.state.storage
    assert isinstance(storage, InMemoryStorage)
    assert storage.get(stolen_reference) == unique_bytes


def test_legitimate_upload_still_works(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "sec-upload@example.com")
    response = _upload(client, headers)
    assert response.status_code == 200
    body = response.json()
    assert body["id"]
    assert body["user_id"] == _user_id
    assert "reference" not in body


def test_upload_assigns_distinct_storage_references(
    client: TestClient, sqlite_engine
) -> None:
    _user_id, headers = register_and_auth(client, "sec-distinct@example.com")
    first = _upload(client, headers, b"first")
    second = _upload(client, headers, b"second")
    assert first.status_code == 200
    assert second.status_code == 200

    with Session(sqlite_engine) as session:
        first_asset = session.get(MediaAsset, UUID(first.json()["id"]))
        second_asset = session.get(MediaAsset, UUID(second.json()["id"]))
        assert first_asset is not None
        assert second_asset is not None
        assert first_asset.reference != second_asset.reference
