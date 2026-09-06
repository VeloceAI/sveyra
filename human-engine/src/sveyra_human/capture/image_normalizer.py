"""Getting an image into the engine.

Accepts a numpy array, a filesystem path, or raw bytes. Deliberately no cloud
storage client: fetching a blob is the caller's problem, and building it in here
would tie the engine to a vendor.
"""

from __future__ import annotations

import io
from pathlib import Path

import numpy as np


def load_image(source: object) -> np.ndarray:
    """Return an HxWx3 uint8 RGB array."""
    if isinstance(source, np.ndarray):
        return _normalise_array(source)
    if isinstance(source, (str, Path)):
        return _decode(Path(source).read_bytes())
    if isinstance(source, (bytes, bytearray)):
        return _decode(bytes(source))
    raise TypeError(f"cannot load an image from {type(source).__name__}")


def _normalise_array(array: np.ndarray) -> np.ndarray:
    if array.ndim == 2:
        array = np.stack([array] * 3, axis=-1)
    if array.ndim != 3 or array.shape[2] < 3:
        raise ValueError("image array must be HxW, HxWx3 or HxWx4")
    rgb = array[:, :, :3]
    if rgb.dtype != np.uint8:
        scale = 255.0 if rgb.max() <= 1.5 else 1.0
        rgb = np.clip(rgb.astype(np.float64) * scale, 0, 255).astype(np.uint8)
    return np.ascontiguousarray(rgb)


def _decode(payload: bytes) -> np.ndarray:
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError(
            "Decoding image files needs Pillow. Install it, or pass a numpy array."
        ) from exc
    with Image.open(io.BytesIO(payload)) as handle:
        return np.asarray(handle.convert("RGB"))
