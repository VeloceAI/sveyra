from datetime import timedelta
from uuid import uuid4

from google.api_core.exceptions import Forbidden, GoogleAPIError, NotFound
from google.auth.exceptions import DefaultCredentialsError
from google.cloud import storage

from app.storage.errors import StorageObjectNotFoundError, StorageUnavailableError
from app.storage.port import validate_access_url_ttl


class GoogleCloudStorage:
    """Production object storage adapter. Uses Application Default Credentials."""

    def __init__(
        self,
        bucket_name: str,
        object_prefix: str = "",
        client: storage.Client | None = None,
    ) -> None:
        self._bucket_name = bucket_name
        self._object_prefix = object_prefix
        self._client = client if client is not None else storage.Client()

    def put(self, data: bytes) -> str:
        reference = f"asset_{uuid4()}"
        blob = self._client.bucket(self._bucket_name).blob(self._object_name(reference))
        try:
            blob.upload_from_string(bytes(data))
        except NotFound:
            raise StorageUnavailableError
        except (DefaultCredentialsError, Forbidden, GoogleAPIError):
            raise StorageUnavailableError
        return reference

    def get(self, reference: str) -> bytes:
        blob = self._client.bucket(self._bucket_name).blob(self._object_name(reference))
        try:
            return bytes(blob.download_as_bytes())
        except NotFound:
            raise StorageObjectNotFoundError
        except (DefaultCredentialsError, Forbidden, GoogleAPIError):
            raise StorageUnavailableError

    def create_access_url(self, reference: str, expires_seconds: int) -> str:
        validate_access_url_ttl(expires_seconds)
        blob = self._client.bucket(self._bucket_name).blob(self._object_name(reference))
        try:
            if not blob.exists():
                raise StorageObjectNotFoundError
            return blob.generate_signed_url(
                version="v4",
                expiration=timedelta(seconds=expires_seconds),
                method="GET",
            )
        except NotFound:
            raise StorageObjectNotFoundError
        except (DefaultCredentialsError, Forbidden, GoogleAPIError):
            raise StorageUnavailableError

    def delete(self, reference: str) -> None:
        blob = self._client.bucket(self._bucket_name).blob(self._object_name(reference))
        try:
            blob.delete()
        except NotFound:
            return
        except (DefaultCredentialsError, Forbidden, GoogleAPIError):
            raise StorageUnavailableError

    def _object_name(self, reference: str) -> str:
        return f"{self._object_prefix}{reference}"
