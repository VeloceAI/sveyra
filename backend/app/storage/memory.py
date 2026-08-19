from uuid import uuid4

from app.storage.errors import StorageObjectNotFoundError
from app.storage.port import validate_access_url_ttl


class InMemoryStorage:
    """Ephemeral process-local adapter for development and tests. Not production storage."""

    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    def put(self, data: bytes) -> str:
        reference = f"asset_{uuid4()}"
        self._objects[reference] = bytes(data)
        return reference

    def get(self, reference: str) -> bytes:
        stored = self._objects.get(reference)
        if stored is None:
            raise StorageObjectNotFoundError
        return bytes(stored)

    def create_access_url(self, reference: str, expires_seconds: int) -> str:
        validate_access_url_ttl(expires_seconds)
        if reference not in self._objects:
            raise StorageObjectNotFoundError
        return f"memory://{reference}"

    def delete(self, reference: str) -> None:
        self._objects.pop(reference, None)
