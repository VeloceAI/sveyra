"""Try-on provider contract.

The core avatar engine never imports a provider. An application picks one and
passes it in, so removing Vertex is a configuration change rather than a code
change.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class TryOnProvider(Protocol):
    """Produces a 2D try-on image. Never a source of 3D body truth."""

    name: str

    def generate(
        self,
        person_image: object,
        garment_image: object,
        options: dict[str, object] | None = None,
    ) -> bytes:
        """Return encoded image bytes of the person wearing the garment."""
        ...
