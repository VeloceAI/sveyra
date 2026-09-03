"""Comparing an observed silhouette against the model's.

The comparison is made on width-per-height profiles rather than on raw pixels.
That is what a silhouette actually measures, it is cheap enough to evaluate
hundreds of times inside a solve, and it degrades gracefully when a mask is
imperfect around the edges.
"""

from __future__ import annotations

import numpy as np

from sveyra_human.camera.projection import (
    OrthographicCamera,
    mask_extent_profile,
    projected_extent_profile,
)

# Fraction of standing height over which the torso is unobstructed. Below the
# armpit the front silhouette is the trunk alone; above it the outstretched arms
# dominate and say nothing about torso width.
TORSO_BAND_RANGE = (0.44, 0.72)


def mask_to_band_profile(mask: np.ndarray, camera: OrthographicCamera, bands: int) -> np.ndarray:
    """Observed width per band, in centimetres.

    Takes the widest row inside each band, matching how the model profile is
    sampled, so the two are compared on the same footing.
    """
    if bands < 2:
        raise ValueError("bands must be at least 2")
    extent = mask_extent_profile(mask) / camera.pixels_per_cm
    filled = np.nonzero(extent)[0]
    if filled.size == 0:
        return np.zeros(bands)

    top, bottom = int(filled.min()), int(filled.max())
    span = bottom - top
    if span <= 0:
        return np.zeros(bands)

    widths = np.zeros(bands)
    for b in range(bands):
        # Band 0 is the feet, and image rows grow downward.
        row_lo = bottom - (b + 1) / bands * span
        row_hi = bottom - b / bands * span
        segment = extent[int(np.floor(row_lo)) : int(np.ceil(row_hi)) + 1]
        if segment.size:
            widths[b] = float(segment.max())
    return widths


def torso_band_slice(bands: int) -> slice:
    """The band indices that see torso and nothing else."""
    lo = int(np.floor(TORSO_BAND_RANGE[0] * bands))
    hi = int(np.ceil(TORSO_BAND_RANGE[1] * bands))
    return slice(max(lo, 0), min(hi, bands))


def model_profile(
    mesh_vertices: np.ndarray,
    mesh_faces: np.ndarray,
    camera: OrthographicCamera,
    bands: int,
) -> np.ndarray:
    return projected_extent_profile(mesh_vertices, mesh_faces, camera, bands)


def profile_residual(
    model: np.ndarray, target: np.ndarray, band_slice: slice | None = None
) -> np.ndarray:
    """Per-band difference in centimetres, restricted to the usable bands."""
    if model.shape != target.shape:
        raise ValueError("model and target profiles must have the same length")
    if band_slice is None:
        return model - target
    return model[band_slice] - target[band_slice]
