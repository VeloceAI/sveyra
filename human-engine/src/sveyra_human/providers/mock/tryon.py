"""Deterministic provider for tests and offline development."""

from __future__ import annotations

import hashlib


class MockTryOnProvider:
    """Returns a stable byte string. Does not render anything.

    Exists so the provider seam can be exercised without credentials, and so a
    test can assert which provider ran.
    """

    name = "mock"

    def generate(
        self,
        person_image: object,
        garment_image: object,
        options: dict[str, object] | None = None,
    ) -> bytes:
        digest = hashlib.sha256(repr((person_image, garment_image, options)).encode()).hexdigest()
        return f"mock-tryon:{digest}".encode()
