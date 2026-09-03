"""Vertex transport.

Isolated so the dependency on a Google SDK exists in exactly one file. The core
engine cannot import this package, and a test enforces that.

Credentials come from Application Default Credentials or workload identity,
never from source and never from a checked-in file.
"""

from __future__ import annotations

import base64
from typing import Any

from sveyra_human.providers.vertex.config import VertexConfig


class VertexClient:
    """Thin wrapper over the Vertex prediction endpoint.

    The SDK is imported lazily: installing this package must not require a cloud
    SDK, and a missing install should fail with an instruction rather than an
    ImportError at module load.
    """

    def __init__(self, config: VertexConfig, transport: Any | None = None) -> None:
        self._config = config
        self._transport = transport

    def _ensure(self) -> Any:
        if self._transport is None:
            try:
                from google.cloud import aiplatform
            except ImportError as exc:  # pragma: no cover - depends on the install
                raise RuntimeError(
                    "The Vertex provider needs google-cloud-aiplatform. Install it, "
                    "or set TRYON_PROVIDER=mock."
                ) from exc
            aiplatform.init(
                project=self._config.project_id, location=self._config.location
            )
            self._transport = aiplatform
        return self._transport

    def predict(self, person_png: bytes, garment_png: bytes) -> bytes:
        """Return the generated image bytes."""
        transport = self._ensure()
        endpoint = transport.Endpoint(self._config.model)
        response = endpoint.predict(
            instances=[
                {
                    "personImage": base64.b64encode(person_png).decode("ascii"),
                    "productImage": base64.b64encode(garment_png).decode("ascii"),
                }
            ]
        )
        return _extract_image(response)


def _extract_image(response: Any) -> bytes:
    """Pull image bytes out of a prediction response.

    Kept separate and defensive because response shapes differ between model
    versions, and a silent shape change should raise here rather than return
    something that is not an image.
    """
    predictions = getattr(response, "predictions", None)
    if not predictions:
        raise RuntimeError("Vertex returned no predictions")
    first = predictions[0]
    payload = None
    if isinstance(first, dict):
        for key in ("bytesBase64Encoded", "image", "generatedImage"):
            if key in first:
                payload = first[key]
                break
    elif isinstance(first, str):
        payload = first
    if payload is None:
        raise RuntimeError("Vertex response did not contain an image")
    if isinstance(payload, bytes):
        return payload
    return base64.b64decode(payload)
