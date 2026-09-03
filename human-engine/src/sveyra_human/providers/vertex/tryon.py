"""Vertex try-on provider. Phase 8 - not implemented.

Present so the seam is real and testable, and so nothing later needs to invent
a new shape for it.
"""

from __future__ import annotations

from sveyra_human.api.errors import NotImplementedYetError


class VertexTryOnProvider:
    name = "vertex"

    def __init__(self, config: object | None = None) -> None:
        self._config = config

    def generate(
        self,
        person_image: object,
        garment_image: object,
        options: dict[str, object] | None = None,
    ) -> bytes:
        raise NotImplementedYetError(
            "Vertex try-on lands in Phase 8. Set TRYON_PROVIDER=mock meanwhile."
        )
