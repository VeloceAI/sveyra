from uuid import uuid4

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.core.errors import UserNotFoundError
from app.models.user import User
from app.services.media_asset_service import MediaAssetService
from app.storage.errors import StorageObjectNotFoundError
from app.storage.memory import InMemoryStorage


def test_put_get_round_trip() -> None:
    storage = InMemoryStorage()
    payload = b"example image bytes"
    reference = storage.put(payload)
    assert storage.get(reference) == payload


def test_reference_is_opaque() -> None:
    storage = InMemoryStorage()
    reference = storage.put(b"example image bytes")
    assert isinstance(reference, str)
    assert reference
    lowered = reference.lower()
    assert not lowered.startswith("http://")
    assert not lowered.startswith("https://")
    assert "://" not in reference
    assert "\\" not in reference
    assert not reference.startswith("/")
    assert ":\\" not in reference
    for token in ("s3", "firebase", "cloudinary", "gcs", "azure", "amazonaws"):
        assert token not in lowered


def test_missing_reference_raises_storage_error() -> None:
    storage = InMemoryStorage()
    with pytest.raises(StorageObjectNotFoundError):
        storage.get("asset_missing")


def test_multiple_objects_have_distinct_references() -> None:
    storage = InMemoryStorage()
    first_ref = storage.put(b"one")
    second_ref = storage.put(b"two")
    assert first_ref != second_ref
    assert storage.get(first_ref) == b"one"
    assert storage.get(second_ref) == b"two"


def test_empty_bytes_are_allowed() -> None:
    storage = InMemoryStorage()
    reference = storage.put(b"")
    assert storage.get(reference) == b""


def test_create_access_url_returns_memory_scheme() -> None:
    storage = InMemoryStorage()
    reference = storage.put(b"example image bytes")
    url = storage.create_access_url(reference, 900)
    assert url == f"memory://{reference}"


def test_create_access_url_missing_reference_raises() -> None:
    storage = InMemoryStorage()
    with pytest.raises(StorageObjectNotFoundError):
        storage.create_access_url("asset_missing", 900)


def test_create_access_url_rejects_invalid_ttl() -> None:
    storage = InMemoryStorage()
    reference = storage.put(b"example image bytes")
    with pytest.raises(ValueError, match="expires_seconds"):
        storage.create_access_url(reference, 0)
    with pytest.raises(ValueError, match="expires_seconds"):
        storage.create_access_url(reference, 3601)


def test_delete_removes_object() -> None:
    storage = InMemoryStorage()
    reference = storage.put(b"example image bytes")
    storage.delete(reference)
    with pytest.raises(StorageObjectNotFoundError):
        storage.get(reference)


def test_delete_missing_reference_is_idempotent() -> None:
    storage = InMemoryStorage()
    storage.delete("asset_missing")


def test_delete_does_not_affect_other_objects() -> None:
    storage = InMemoryStorage()
    first_ref = storage.put(b"one")
    second_ref = storage.put(b"two")
    storage.delete(first_ref)
    assert storage.get(second_ref) == b"two"
    with pytest.raises(StorageObjectNotFoundError):
        storage.get(first_ref)


def test_create_asset_from_bytes_persists_opaque_reference(sqlite_engine) -> None:
    factory = sessionmaker(
        bind=sqlite_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    session: Session = factory()
    storage = InMemoryStorage()
    service = MediaAssetService(storage=storage)
    user = User(id=uuid4(), email="storage-user@example.com", password_hash="x")
    session.add(user)
    session.commit()

    payload = b"example image bytes"
    created = service.create_asset_from_bytes(session, user.id, payload)

    assert created.user_id == user.id
    assert created.reference
    assert not created.reference.lower().startswith("http")
    assert storage.get(created.reference) == payload
    fetched = service.get_asset(session, created.id, user.id)
    assert fetched.reference == created.reference
    assert "bytes" not in fetched.model_dump()
    session.close()


def test_create_asset_from_bytes_rejects_missing_user(sqlite_engine) -> None:
    factory = sessionmaker(
        bind=sqlite_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    session: Session = factory()
    service = MediaAssetService(storage=InMemoryStorage())
    with pytest.raises(UserNotFoundError):
        service.create_asset_from_bytes(session, uuid4(), b"example image bytes")
    session.close()
