from typing import Protocol

MAX_ACCESS_URL_TTL_SECONDS = 3600


def validate_access_url_ttl(expires_seconds: int) -> None:
    if expires_seconds <= 0 or expires_seconds > MAX_ACCESS_URL_TTL_SECONDS:
        raise ValueError(
            f"expires_seconds must be between 1 and {MAX_ACCESS_URL_TTL_SECONDS}"
        )


class StoragePort(Protocol):
    def put(self, data: bytes) -> str:
        """Store bytes and return an opaque provider-neutral reference."""

    def get(self, reference: str) -> bytes:
        """Return stored bytes. For tests and internal use only, not a public download API."""

    def create_access_url(self, reference: str, expires_seconds: int) -> str:
        """Return a short-lived access URL. Ephemeral; must not be persisted."""

    def delete(self, reference: str) -> None:
        """Delete stored bytes. Idempotent when the object is already absent."""
