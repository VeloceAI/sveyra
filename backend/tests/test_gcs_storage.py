from unittest.mock import MagicMock

import pytest
from google.api_core.exceptions import Forbidden, GoogleAPIError, NotFound
from google.auth.exceptions import DefaultCredentialsError

from app.storage.errors import StorageObjectNotFoundError, StorageUnavailableError
from app.storage.gcs import GoogleCloudStorage


def _make_storage(
    bucket_name: str = "test-bucket",
    object_prefix: str = "media/",
    client: MagicMock | None = None,
) -> tuple[GoogleCloudStorage, MagicMock, MagicMock]:
    mock_client = client or MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob
    storage = GoogleCloudStorage(
        bucket_name=bucket_name,
        object_prefix=object_prefix,
        client=mock_client,
    )
    return storage, mock_client, mock_blob


def test_put_uploads_bytes_and_returns_opaque_reference() -> None:
    storage, mock_client, mock_blob = _make_storage()
    payload = b"example image bytes"
    reference = storage.put(payload)
    mock_client.bucket.assert_called_with("test-bucket")
    mock_blob.upload_from_string.assert_called_once_with(payload)
    assert reference.startswith("asset_")
    assert not reference.lower().startswith("http")
    assert not reference.lower().startswith("gs://")
    assert "test-bucket" not in reference
    assert mock_client.bucket.return_value.blob.called
    object_name = mock_client.bucket.return_value.blob.call_args[0][0]
    assert object_name == f"media/{reference}"


def test_get_returns_downloaded_bytes() -> None:
    storage, _, mock_blob = _make_storage()
    mock_blob.download_as_bytes.return_value = b"stored bytes"
    assert storage.get("asset_abc") == b"stored bytes"
    mock_blob.download_as_bytes.assert_called_once()


def test_get_missing_object_raises_storage_object_not_found() -> None:
    storage, _, mock_blob = _make_storage()
    mock_blob.download_as_bytes.side_effect = NotFound("missing")
    with pytest.raises(StorageObjectNotFoundError):
        storage.get("asset_missing")


def test_put_auth_failure_raises_storage_unavailable() -> None:
    storage, _, mock_blob = _make_storage()
    mock_blob.upload_from_string.side_effect = DefaultCredentialsError("no creds")
    with pytest.raises(StorageUnavailableError):
        storage.put(b"bytes")


def test_get_permission_failure_raises_storage_unavailable() -> None:
    storage, _, mock_blob = _make_storage()
    mock_blob.download_as_bytes.side_effect = Forbidden("denied")
    with pytest.raises(StorageUnavailableError):
        storage.get("asset_denied")


def test_put_generic_api_failure_raises_storage_unavailable() -> None:
    storage, _, mock_blob = _make_storage()
    mock_blob.upload_from_string.side_effect = GoogleAPIError("api down")
    with pytest.raises(StorageUnavailableError):
        storage.put(b"bytes")


def test_multiple_puts_return_distinct_references() -> None:
    storage, _, mock_blob = _make_storage()
    first = storage.put(b"one")
    second = storage.put(b"two")
    assert first != second
    assert first.startswith("asset_")
    assert second.startswith("asset_")


def test_empty_bytes_are_allowed() -> None:
    storage, _, mock_blob = _make_storage()
    mock_blob.download_as_bytes.return_value = b""
    reference = storage.put(b"")
    mock_blob.upload_from_string.assert_called_once_with(b"")
    assert storage.get(reference) == b""


def test_create_access_url_generates_signed_url() -> None:
    storage, mock_client, mock_blob = _make_storage()
    mock_blob.exists.return_value = True
    mock_blob.generate_signed_url.return_value = "https://storage.googleapis.com/signed"
    reference = "asset_abc"
    url = storage.create_access_url(reference, 900)
    mock_client.bucket.assert_called_with("test-bucket")
    mock_blob.exists.assert_called_once()
    mock_blob.generate_signed_url.assert_called_once()
    call_kwargs = mock_blob.generate_signed_url.call_args.kwargs
    assert call_kwargs["version"] == "v4"
    assert call_kwargs["method"] == "GET"
    assert call_kwargs["expiration"].total_seconds() == 900
    assert url == "https://storage.googleapis.com/signed"
    assert mock_client.bucket.return_value.blob.call_args[0][0] == "media/asset_abc"


def test_create_access_url_missing_object_raises_not_found() -> None:
    storage, _, mock_blob = _make_storage()
    mock_blob.exists.return_value = False
    with pytest.raises(StorageObjectNotFoundError):
        storage.create_access_url("asset_missing", 900)


def test_create_access_url_auth_failure_raises_storage_unavailable() -> None:
    storage, _, mock_blob = _make_storage()
    mock_blob.exists.return_value = True
    mock_blob.generate_signed_url.side_effect = DefaultCredentialsError("no creds")
    with pytest.raises(StorageUnavailableError):
        storage.create_access_url("asset_abc", 900)


def test_delete_calls_blob_delete_with_prefixed_object_name() -> None:
    storage, mock_client, mock_blob = _make_storage()
    storage.delete("asset_abc")
    mock_client.bucket.assert_called_with("test-bucket")
    mock_blob.delete.assert_called_once()
    assert mock_client.bucket.return_value.blob.call_args[0][0] == "media/asset_abc"


def test_delete_missing_object_is_idempotent() -> None:
    storage, _, mock_blob = _make_storage()
    mock_blob.delete.side_effect = NotFound("missing")
    storage.delete("asset_missing")
    mock_blob.delete.assert_called_once()


def test_delete_auth_failure_raises_storage_unavailable() -> None:
    storage, _, mock_blob = _make_storage()
    mock_blob.delete.side_effect = DefaultCredentialsError("no creds")
    with pytest.raises(StorageUnavailableError):
        storage.delete("asset_abc")


def test_delete_permission_failure_raises_storage_unavailable() -> None:
    storage, _, mock_blob = _make_storage()
    mock_blob.delete.side_effect = Forbidden("denied")
    with pytest.raises(StorageUnavailableError):
        storage.delete("asset_denied")
