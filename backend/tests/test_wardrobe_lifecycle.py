from uuid import uuid4

from uuid import UUID

from fastapi.testclient import TestClient

from sqlalchemy.orm import Session, sessionmaker

from app.models.media_asset import MediaAsset
from app.storage.deps import get_storage
from app.storage.errors import StorageObjectNotFoundError, StorageUnavailableError
from app.storage.memory import InMemoryStorage
from tests.auth_helpers import register_and_auth

UPLOAD_BYTES = b"wardrobe-lifecycle-bytes"


def _item_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "category": "shirt",
        "color": "navy",
        "brand": "unbranded",
        "attributes": {},
    }
    payload.update(overrides)
    return payload


def _create_item(client: TestClient, headers: dict[str, str], **overrides: object) -> dict:
    response = client.post("/v1/wardrobe", json=_item_payload(**overrides), headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def _upload_linked(
    client: TestClient, headers: dict[str, str], item_id: str, payload: bytes = UPLOAD_BYTES
) -> dict:
    response = client.post(
        "/v1/media/upload",
        headers=headers,
        data={"wardrobe_item_id": item_id},
        files={"file": ("garment.jpg", payload, "image/jpeg")},
    )
    assert response.status_code == 200, response.text
    return response.json()


class FailingDeleteStorage(InMemoryStorage):
    def delete(self, reference: str) -> None:
        raise StorageUnavailableError


def test_patch_updates_partial_fields(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "patch-user@example.com")
    item = _create_item(client, headers)
    response = client.patch(
        f"/v1/wardrobe/{item['id']}",
        headers=headers,
        json={"color": "black", "attributes": {"fit": "slim"}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "shirt"
    assert body["brand"] == "unbranded"
    assert body["color"] == "black"
    assert body["attributes"] == {"fit": "slim"}
    fetched = client.get(f"/v1/wardrobe/{item['id']}", headers=headers).json()
    assert fetched["color"] == "black"
    assert fetched["attributes"] == {"fit": "slim"}


def test_patch_rejects_empty_body(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "patch-empty@example.com")
    item = _create_item(client, headers)
    response = client.patch(f"/v1/wardrobe/{item['id']}", headers=headers, json={})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_patch_rejects_unknown_fields(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "patch-extra@example.com")
    item = _create_item(client, headers)
    response = client.patch(
        f"/v1/wardrobe/{item['id']}",
        headers=headers,
        json={"color": "black", "user_id": str(uuid4())},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_patch_rejects_unsafe_attributes(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "patch-unsafe@example.com")
    item = _create_item(client, headers)
    response = client.patch(
        f"/v1/wardrobe/{item['id']}",
        headers=headers,
        json={"attributes": {"image": "https://evil.example/x"}},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_patch_requires_jwt(client: TestClient) -> None:
    response = client.patch(f"/v1/wardrobe/{uuid4()}", json={"color": "black"})
    assert response.status_code == 401


def test_patch_foreign_item_returns_404(client: TestClient) -> None:
    _user_a, headers_a = register_and_auth(client, "patch-a@example.com")
    _user_b, headers_b = register_and_auth(client, "patch-b@example.com")
    item_a = _create_item(client, headers_a)
    response = client.patch(
        f"/v1/wardrobe/{item_a['id']}",
        headers=headers_b,
        json={"color": "red"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "wardrobe_item_not_found"


def test_delete_returns_204_and_removes_item(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "delete-user@example.com")
    item = _create_item(client, headers)
    response = client.delete(f"/v1/wardrobe/{item['id']}", headers=headers)
    assert response.status_code == 204
    assert response.content == b""
    missing = client.get(f"/v1/wardrobe/{item['id']}", headers=headers)
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "wardrobe_item_not_found"


def _reference_for_asset(sqlite_engine, asset_id: str) -> str:
    factory = sessionmaker(bind=sqlite_engine, autoflush=False, autocommit=False)
    with factory() as session:
        asset = session.get(MediaAsset, UUID(asset_id))
        assert asset is not None
        return asset.reference


def test_delete_cascades_linked_media(client: TestClient, sqlite_engine) -> None:
    _user_id, headers = register_and_auth(client, "delete-media@example.com")
    item = _create_item(client, headers)
    asset = _upload_linked(client, headers, item["id"])
    storage = client.app.state.storage
    assert isinstance(storage, InMemoryStorage)
    reference = _reference_for_asset(sqlite_engine, asset["id"])
    assert storage.get(reference) == UPLOAD_BYTES

    response = client.delete(f"/v1/wardrobe/{item['id']}", headers=headers)
    assert response.status_code == 204
    media = client.get(f"/v1/media/{asset['id']}", headers=headers)
    assert media.status_code == 404
    assert media.json()["error"]["code"] == "media_asset_not_found"
    try:
        storage.get(reference)
        assert False, "expected storage object to be gone"
    except StorageObjectNotFoundError:
        pass


def test_delete_storage_failure_preserves_item_and_media(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "delete-fail@example.com")
    item = _create_item(client, headers)
    asset = _upload_linked(client, headers, item["id"])
    failing = FailingDeleteStorage()
    failing._objects = dict(client.app.state.storage._objects)
    client.app.state.storage = failing
    client.app.dependency_overrides[get_storage] = lambda: failing

    response = client.delete(f"/v1/wardrobe/{item['id']}", headers=headers)
    client.app.dependency_overrides.pop(get_storage, None)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "storage_unavailable"
    assert client.get(f"/v1/wardrobe/{item['id']}", headers=headers).status_code == 200
    assert client.get(f"/v1/media/{asset['id']}", headers=headers).status_code == 200


def test_delete_foreign_item_returns_404(client: TestClient) -> None:
    _user_a, headers_a = register_and_auth(client, "delete-a@example.com")
    _user_b, headers_b = register_and_auth(client, "delete-b@example.com")
    item_a = _create_item(client, headers_a)
    response = client.delete(f"/v1/wardrobe/{item_a['id']}", headers=headers_b)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "wardrobe_item_not_found"


def test_delete_requires_jwt(client: TestClient) -> None:
    response = client.delete(f"/v1/wardrobe/{uuid4()}")
    assert response.status_code == 401


def test_delete_does_not_remove_saved_outfit(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "delete-outfit@example.com")
    item = _create_item(client, headers)
    outfit = client.post(
        "/v1/outfits",
        headers=headers,
        json={"occasion": "casual", "item_ids": [item["id"]], "rationale": {"note": "keep"}},
    ).json()
    assert client.delete(f"/v1/wardrobe/{item['id']}", headers=headers).status_code == 204
    fetched = client.get(f"/v1/outfits/{outfit['id']}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["item_ids"] == [item["id"]]


def test_delete_missing_item_returns_404(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "delete-missing@example.com")
    response = client.delete(f"/v1/wardrobe/{uuid4()}", headers=headers)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "wardrobe_item_not_found"
