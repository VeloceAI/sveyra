"""Turning a person mask into something the fitter can use."""

from __future__ import annotations

import numpy as np
from scipy import ndimage

from sveyra_human.vision.port import SegmentationResult


def clean_mask(mask: np.ndarray, min_island_fraction: float = 0.02) -> np.ndarray:
    """Drop specks and close pinholes.

    A segmenter often leaves a few stray blobs where the background varied.
    Anything far smaller than the subject is noise, not a limb.
    """
    if not mask.any():
        return mask.astype(bool)
    filled = ndimage.binary_fill_holes(mask)
    labels, count = ndimage.label(filled)
    if count <= 1:
        return filled.astype(bool)
    sizes = ndimage.sum_labels(filled, labels, index=range(1, count + 1))
    keep = sizes >= sizes.max() * min_island_fraction
    return np.isin(labels, np.nonzero(keep)[0] + 1)


def vertical_extent(mask: np.ndarray) -> tuple[int, int]:
    """Topmost and bottommost filled rows."""
    rows = np.nonzero(mask.any(axis=1))[0]
    if rows.size == 0:
        raise ValueError("mask is empty")
    return int(rows.min()), int(rows.max())


def crop_to_subject(mask: np.ndarray, margin: int = 2) -> np.ndarray:
    """Trim to the subject's bounding box, keeping a small margin."""
    if not mask.any():
        return mask
    rows = np.nonzero(mask.any(axis=1))[0]
    cols = np.nonzero(mask.any(axis=0))[0]
    r0 = max(int(rows.min()) - margin, 0)
    r1 = min(int(rows.max()) + margin + 1, mask.shape[0])
    c0 = max(int(cols.min()) - margin, 0)
    c1 = min(int(cols.max()) + margin + 1, mask.shape[1])
    return mask[r0:r1, c0:c1]


def is_full_body(mask: np.ndarray, min_height_fraction: float = 0.55) -> bool:
    """Whether the subject spans enough of the frame to measure a height against.

    A cropped or half-length photo cannot be scaled by a known standing height,
    so the fitter must not be handed one silently.
    """
    if not mask.any():
        return False
    top, bottom = vertical_extent(mask)
    return (bottom - top + 1) >= mask.shape[0] * min_height_fraction


def silhouette_from_segmentation(result: SegmentationResult) -> np.ndarray:
    return clean_mask(result.mask)
