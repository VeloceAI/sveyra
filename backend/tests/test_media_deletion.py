from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.errors import MediaAssetNotFoundError, MediaDeletionIncompleteError
from app.models.media_asset import MediaAsset
from app.models.user import User
from app.services.media_asset_service import MediaAssetService
from app.storage.deps import get_storage
from app.storage.errors import StorageObjectNotFoundError, StorageUnavailableError
from app.storage.memory import InMemoryStorage
from tests.auth_helpers import register_and_auth

UPLOAD_BYTES = b"example image bytes"


def _upload(client: TestClient, headers: dict[str, str], payload: bytes = UPLOAD_BYTES):
    return client.post(
        "/v1/media/upload",
        headers=headers,
        files={"file": ("garment.jpg", payload, "image/jpeg")},
    )


class FailingDeleteStorage(InMemoryStorage):
    def delete(self, reference: str) -> None:
        raise StorageUnavailableError


class TrackingDeleteStorage(InMemoryStorage):
    def __init__(self) -> None:
        super().__init__()
        self.deleted_references: list[str] = []

    def delete(self, reference: str) -> None:
        self.deleted_references.append(reference)
        super().delete(reference)


def test_service_deletes_storage_then_metadata(sqlite_engine) -> None:
    factory = sessionmaker(
        bind=sqlite_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    session: Session = factory()
    storage = InMemoryStorage()
    service = MediaAssetService(storage=storage)
    user = User(id=uuid4(), email="delete-service@example.com", password_hash="x")
    session.add(user)
    session.commit()

    created = service.create_asset_from_bytes(session, user.id, UPLOAD_BYTES)
    reference = created.reference
    service.delete_asset(session, created.id, user.id)

    assert session.get(MediaAsset, created.id) is None
    with pytest.raises(StorageObjectNotFoundError):
        storage.get(reference)
    session.close()


def test_service_uses_stored_reference_for_storage_delete(sqlite_engine) -> None:
    factory = sessionmaker(
        bind=sqlite_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    session: Session = factory()
    storage = TrackingDeleteStorage()
    service = MediaAssetService(storage=storage)
    user = User(id=uuid4(), email="delete-ref@example.com", password_hash="x")
    session.add(user)
    session.commit()

    created = service.create_asset_from_bytes(session, user.id, UPLOAD_BYTES)
    service.delete_asset(session, created.id, user.id)

    assert storage.deleted_references == [created.reference]
    session.close()


def test_service_storage_failure_prevents_metadata_deletion(sqlite_engine) -> None:
    factory = sessionmaker(
        bind=sqlite_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    session: Session = factory()
    storage = FailingDeleteStorage()
    service = MediaAssetService(storage=storage)
    user = User(id=uuid4(), email="delete-fail@example.com", password_hash="x")
    session.add(user)
    session.commit()

    created = service.create_asset_from_bytes(session, user.id, UPLOAD_BYTES)
    with pytest.raises(StorageUnavailableError):
        service.delete_asset(session, created.id, user.id)

    assert session.get(MediaAsset, created.id) is not None
    assert storage.get(created.reference) == UPLOAD_BYTES
    session.close()


def test_service_missing_asset_raises_not_found(sqlite_engine) -> None:
    factory = sessionmaker(
        bind=sqlite_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    session: Session = factory()
    service = MediaAssetService(storage=InMemoryStorage())
    with pytest.raises(MediaAssetNotFoundError):
        service.delete_asset(session, uuid4(), uuid4())
    session.close()


def test_delete_success_returns_204_and_removes_metadata_and_object(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "delete-user@example.com")
    upload = _upload(client, headers).json()
    asset_id = upload["id"]
    reference = upload["reference"]
    storage = client.app.state.storage

    response = client.delete(f"/v1/media/{asset_id}", headers=headers)
    assert response.status_code == 204
    assert response.content == b""

    metadata_response = client.get(f"/v1/media/{asset_id}", headers=headers)
    assert metadata_response.status_code == 404
    assert metadata_response.json() == {
        "error": {"code": "media_asset_not_found", "message": "Media asset was not found."}
    }
    with pytest.raises(StorageObjectNotFoundError):
        storage.get(reference)


def test_delete_missing_asset_returns_not_found(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "delete-user@example.com")
    response = client.delete(f"/v1/media/{uuid4()}", headers=headers)
    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "media_asset_not_found", "message": "Media asset was not found."}
    }


def test_cannot_delete_another_users_media(client: TestClient) -> None:
    _user_a, headers_a = register_and_auth(client, "delete-a@example.com")
    _user_b, headers_b = register_and_auth(client, "delete-b@example.com")
    asset_id = _upload(client, headers_a).json()["id"]
    response = client.delete(f"/v1/media/{asset_id}", headers=headers_b)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "media_asset_not_found"
    assert client.get(f"/v1/media/{asset_id}", headers=headers_a).status_code == 200


def test_delete_storage_failure_preserves_metadata(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "delete-user@example.com")
    upload = _upload(client, headers).json()
    asset_id = upload["id"]
    shared_storage = client.app.state.storage
    failing_storage = FailingDeleteStorage()
    failing_storage._objects = shared_storage._objects
    client.app.dependency_overrides[get_storage] = lambda: failing_storage

    response = client.delete(f"/v1/media/{asset_id}", headers=headers)
    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "storage_unavailable",
            "message": "Media storage is temporarily unavailable.",
        }
    }

    metadata = client.get(f"/v1/media/{asset_id}", headers=headers)
    assert metadata.status_code == 200
    assert metadata.json()["id"] == asset_id

    client.app.dependency_overrides.pop(get_storage, None)


def test_http_retry_after_storage_failure_completes_deletion(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "delete-user@example.com")
    upload = _upload(client, headers).json()
    asset_id = upload["id"]
    reference = upload["reference"]
    shared_storage = client.app.state.storage
    failing_storage = FailingDeleteStorage()
    failing_storage._objects = shared_storage._objects
    client.app.dependency_overrides[get_storage] = lambda: failing_storage

    first = client.delete(f"/v1/media/{asset_id}", headers=headers)
    assert first.status_code == 503
    client.app.dependency_overrides.pop(get_storage, None)

    retry = client.delete(f"/v1/media/{asset_id}", headers=headers)
    assert retry.status_code == 204
    assert client.get(f"/v1/media/{asset_id}", headers=headers).status_code == 404
    with pytest.raises(StorageObjectNotFoundError):
        shared_storage.get(reference)


def test_http_retry_when_object_already_missing_removes_metadata(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "delete-user@example.com")
    upload = _upload(client, headers).json()
    asset_id = upload["id"]
    reference = upload["reference"]
    storage = client.app.state.storage
    storage.delete(reference)

    response = client.delete(f"/v1/media/{asset_id}", headers=headers)
    assert response.status_code == 204
    assert client.get(f"/v1/media/{asset_id}", headers=headers).status_code == 404


def test_service_retry_after_storage_failure(sqlite_engine) -> None:
    factory = sessionmaker(
        bind=sqlite_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    session: Session = factory()
    failing = FailingDeleteStorage()
    service = MediaAssetService(storage=failing)
    user = User(id=uuid4(), email="retry-storage@example.com", password_hash="x")
    session.add(user)
    session.commit()

    created = service.create_asset_from_bytes(session, user.id, UPLOAD_BYTES)
    with pytest.raises(StorageUnavailableError):
        service.delete_asset(session, created.id, user.id)
    assert session.get(MediaAsset, created.id) is not None

    recovered = InMemoryStorage()
    recovered._objects = failing._objects
    MediaAssetService(storage=recovered).delete_asset(session, created.id, user.id)
    assert session.get(MediaAsset, created.id) is None
    with pytest.raises(StorageObjectNotFoundError):
        recovered.get(created.reference)
    session.close()


def test_service_retry_when_object_already_missing(sqlite_engine) -> None:
    factory = sessionmaker(
        bind=sqlite_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    session: Session = factory()
    storage = InMemoryStorage()
    service = MediaAssetService(storage=storage)
    user = User(id=uuid4(), email="retry-missing@example.com", password_hash="x")
    session.add(user)
    session.commit()

    created = service.create_asset_from_bytes(session, user.id, UPLOAD_BYTES)
    storage.delete(created.reference)
    service.delete_asset(session, created.id, user.id)

    assert session.get(MediaAsset, created.id) is None
    session.close()


def test_commit_failure_leaves_metadata_and_retry_recovers(sqlite_engine) -> None:
    factory = sessionmaker(
        bind=sqlite_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    session: Session = factory()
    storage = InMemoryStorage()
    service = MediaAssetService(storage=storage)
    user = User(id=uuid4(), email="retry-commit@example.com", password_hash="x")
    session.add(user)
    session.commit()

    created = service.create_asset_from_bytes(session, user.id, UPLOAD_BYTES)
    original_commit = session.commit

    def fail_once() -> None:
        session.commit = original_commit
        raise SQLAlchemyError("commit failed")

    session.commit = fail_once  # type: ignore[method-assign]
    with pytest.raises(MediaDeletionIncompleteError):
        service.delete_asset(session, created.id, user.id)

    remaining = session.get(MediaAsset, created.id)
    assert remaining is not None
    assert remaining.reference == created.reference

    service.delete_asset(session, created.id, user.id)
    assert session.get(MediaAsset, created.id) is None
    with pytest.raises(StorageObjectNotFoundError):
        storage.get(created.reference)
    session.close()
