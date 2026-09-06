"""Building hair volumes over the fitted skull.

Thickness comes from the photograph: the hair silhouette is wider than the bare
head by roughly twice the hair depth, so the difference measures it. Where the
photograph does not show a group, that group is not built.
"""

from __future__ import annotations

import numpy as np

from sveyra_human.body.cage import CagePart
from sveyra_human.hair.groups import (
    GROUP_REGIONS,
    HairGroup,
    HairStrandChain,
    Hairstyle,
    HairVolume,
    groups_present,
)

# Hair sits off the scalp by at least this much even when the photograph
# suggests less; a shell at zero offset z-fights with the head.
MIN_THICKNESS_CM = 0.4
MAX_THICKNESS_CM = 12.0


def measure_thickness(
    hair_mask: np.ndarray, head_mask: np.ndarray, pixels_per_cm: float
) -> float:
    """Hair depth in centimetres, from how much wider the hair silhouette is.

    Halved because the silhouette grows on both sides of the head.
    """
    if pixels_per_cm <= 0:
        raise ValueError("pixels_per_cm must be positive")
    if not hair_mask.any() or not head_mask.any():
        return MIN_THICKNESS_CM

    hair_rows = np.nonzero(hair_mask.any(axis=1))[0]
    widths = []
    for row in hair_rows:
        hair_cols = np.nonzero(hair_mask[row])[0]
        head_cols = np.nonzero(head_mask[row])[0]
        if hair_cols.size == 0 or head_cols.size == 0:
            continue
        hair_width = hair_cols.max() - hair_cols.min()
        head_width = head_cols.max() - head_cols.min()
        widths.append(max(0.0, float(hair_width - head_width)) / 2.0)

    if not widths:
        return MIN_THICKNESS_CM
    thickness = float(np.median(widths)) / pixels_per_cm
    return float(np.clip(thickness, MIN_THICKNESS_CM, MAX_THICKNESS_CM))


def _ring_azimuths(ring: np.ndarray, centre: np.ndarray) -> np.ndarray:
    """Angle of each ring vertex around the head, degrees, 0 facing forward (+Z)."""
    offsets = ring - centre
    return np.degrees(np.arctan2(offsets[:, 0], offsets[:, 2]))


def _in_azimuth_range(angles: np.ndarray, low: float, high: float) -> np.ndarray:
    if high - low >= 360.0:
        return np.ones_like(angles, dtype=bool)
    wrapped = (angles - low) % 360.0
    return wrapped <= (high - low) % 360.0


def build_hairstyle(
    head: CagePart,
    thickness_cm: float,
    coverage: dict[HairGroup, float] | None = None,
    chain_nodes: int = 4,
) -> Hairstyle:
    """Offset the skull outward per group to form hair shells."""
    if thickness_cm <= 0:
        raise ValueError("thickness_cm must be positive")

    rings = head.rings
    levels = rings.shape[0]
    heights = rings[:, :, 1].mean(axis=1)
    low, high = float(heights.min()), float(heights.max())
    span = max(high - low, 1e-6)
    centre_xz = rings.reshape(-1, 3).mean(axis=0)

    present = (
        list(GROUP_REGIONS)
        if coverage is None
        else groups_present(coverage)
    )

    volumes: list[HairVolume] = []
    for group in present:
        (az_low, az_high), (h_low, h_high) = GROUP_REGIONS[group]
        selected_levels = [
            i for i in range(levels) if h_low <= (heights[i] - low) / span <= h_high
        ]
        if len(selected_levels) < 2:
            continue

        shell = np.empty((len(selected_levels), rings.shape[1], 3))
        for out_index, level in enumerate(selected_levels):
            ring = rings[level]
            centre = np.array([centre_xz[0], ring[:, 1].mean(), centre_xz[2]])
            radial = ring - centre
            norms = np.linalg.norm(radial, axis=1, keepdims=True)
            norms = np.where(norms < 1e-9, 1e-9, norms)
            angles = _ring_azimuths(ring, centre)
            # Only the arc this group covers is pushed out; the rest stays on
            # the scalp so neighbouring shells meet instead of overlapping.
            amount = np.where(_in_azimuth_range(angles, az_low, az_high), thickness_cm, 0.0)
            shell[out_index] = ring + radial / norms * amount[:, None]

        chains = _build_chains(shell, chain_nodes)
        volumes.append(
            HairVolume(group=group, rings=shell, thickness_cm=thickness_cm, chains=chains)
        )

    return Hairstyle(volumes=volumes)


def _build_chains(shell: np.ndarray, nodes: int, count: int = 3) -> list[HairStrandChain]:
    """A few control chains hanging from the lowest ring of a shell."""
    if shell.shape[0] < 1 or nodes < 2:
        return []
    bottom = shell[0]
    step = max(1, bottom.shape[0] // count)
    chains: list[HairStrandChain] = []
    for index in range(0, bottom.shape[0], step):
        root = bottom[index]
        # Chains hang straight down at rest. A solver moves them from here.
        drop = np.linspace(0.0, 1.0, nodes)[:, None] * np.array([0.0, -3.0, 0.0])
        chains.append(HairStrandChain(root=root, nodes=root + drop))
    return chains
