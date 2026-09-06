"""Vertex try-on provider.

A 2D preview generator, never a source of 3D body truth. The engine's fitted
avatar stays authoritative for measurements, fit and animation; this produces a
photoreal still to sit alongside it.
"""

from __future__ import annotations

import io

import numpy as np

from sveyra_human.providers.vertex.client import VertexClient
from sveyra_human.providers.vertex.config import VertexConfig


def _to_png(source: object) -> bytes:
    """Accept an array, bytes or a path, and hand Vertex encoded PNG bytes."""
    if isinstance(source, bytes):
        return source
    from sveyra_human.capture.image_normalizer import load_image

    array = load_image(source)
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Encoding an image for Vertex needs Pillow.") from exc
    buffer = io.BytesIO()
    Image.fromarray(np.asarray(array)).save(buffer, format="PNG")
    return buffer.getvalue()


class VertexTryOnProvider:
    """Generates a 2D try-on image through Vertex AI."""

    name = "vertex"

    def __init__(
        self, config: VertexConfig | None = None, client: VertexClient | None = None
    ) -> None:
        self._config = config
        self._client = client

    def _ensure_client(self) -> VertexClient:
        if self._client is None:
            config = self._config or VertexConfig.from_env()
            self._client = VertexClient(config)
        return self._client

    def generate(
        self,
        person_image: object,
        garment_image: object,
        options: dict[str, object] | None = None,
    ) -> bytes:
        return self._ensure_client().predict(_to_png(person_image), _to_png(garment_image))
