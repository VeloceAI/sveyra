"""Binding the surface to the skeleton.

Weights come from distance to each bone segment rather than from a painted map,
because the mesh is generated: there is nothing to paint onto that survives a
change in cage resolution. Distance falloff is deterministic, needs no artist,
and is good enough for the rest pose plus moderate articulation.

Each vertex keeps at most four influences, which is what glTF stores and what
GPU skinning expects.
"""

from __future__ import annotations

import numpy as np

from sveyra_human.skeleton.joints import HIERARCHY
from sveyra_human.skeleton.model import Skeleton

MAX_INFLUENCES = 4

# Bones a vertex may actually bind to. The root and clavicles exist to carry
# transforms, not to deform skin near themselves.
DEFORMING_BONES: tuple[str, ...] = (
    "pelvis",
    "spine_1",
    "spine_2",
    "chest",
    "neck",
    "head",
    "upperarm_L",
    "forearm_L",
    "hand_L",
    "upperarm_R",
    "forearm_R",
    "hand_R",
    "thigh_L",
    "calf_L",
    "foot_L",
    "thigh_R",
    "calf_R",
    "foot_R",
)


def bone_segments(skeleton: Skeleton) -> list[tuple[str, np.ndarray, np.ndarray]]:
    """Each deforming bone as a (name, start, end) segment.

    A bone is the span from its parent joint to itself, which is what a vertex
    should measure distance against - measuring to a single joint point makes
    long bones like a thigh lose their grip halfway down.
    """
    segments: list[tuple[str, np.ndarray, np.ndarray]] = []
    for name in DEFORMING_BONES:
        parent = HIERARCHY.get(name)
        if parent is None:
            continue
        segments.append((name, skeleton.positions[parent], skeleton.positions[name]))
    return segments


def _distance_to_segments(
    points: np.ndarray, starts: np.ndarray, ends: np.ndarray
) -> np.ndarray:
    """Perpendicular distance from every point to every segment. (n, b)"""
    axis = ends - starts  # (b, 3)
    length_sq = np.einsum("bi,bi->b", axis, axis)
    length_sq = np.where(length_sq < 1e-12, 1e-12, length_sq)

    delta = points[:, None, :] - starts[None, :, :]  # (n, b, 3)
    t = np.einsum("nbi,bi->nb", delta, axis) / length_sq
    t = np.clip(t, 0.0, 1.0)
    closest = starts[None, :, :] + t[:, :, None] * axis[None, :, :]
    return np.linalg.norm(points[:, None, :] - closest, axis=2)


def compute_skin_weights(
    vertices: np.ndarray, skeleton: Skeleton, falloff: float = 2.5
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Return (joint_indices, weights, bone_names).

    Both arrays are (n, MAX_INFLUENCES). Weights sum to 1 per vertex.
    `falloff` controls how sharply influence decays with distance; higher is
    stiffer and keeps joints from dragging distant geometry.
    """
    segments = bone_segments(skeleton)
    if not segments:
        raise ValueError("skeleton produced no deforming bones")
    names = [name for name, _, _ in segments]
    starts = np.array([s for _, s, _ in segments])
    ends = np.array([e for _, _, e in segments])

    distance = _distance_to_segments(vertices, starts, ends)
    # Inverse-power falloff. The epsilon keeps a vertex sitting exactly on a
    # bone from becoming infinitely weighted.
    influence = 1.0 / np.power(distance + 1e-3, falloff)

    top = np.argsort(-influence, axis=1)[:, :MAX_INFLUENCES]
    rows = np.arange(vertices.shape[0])[:, None]
    weights = influence[rows, top]
    total = weights.sum(axis=1, keepdims=True)
    total = np.where(total < 1e-12, 1.0, total)
    return top.astype(np.uint16), (weights / total).astype(np.float32), names


def validate_weights(indices: np.ndarray, weights: np.ndarray, bone_count: int) -> None:
    """Fail loudly here rather than producing a mesh that explodes in a viewer."""
    if indices.shape != weights.shape:
        raise ValueError("indices and weights must have the same shape")
    if indices.shape[1] != MAX_INFLUENCES:
        raise ValueError(f"expected {MAX_INFLUENCES} influences per vertex")
    if indices.max(initial=0) >= bone_count:
        raise ValueError("a vertex references a joint that does not exist")
    sums = weights.sum(axis=1)
    if not np.allclose(sums, 1.0, atol=1e-4):
        raise ValueError("vertex weights must sum to 1")
    if (weights < 0).any():
        raise ValueError("weights must not be negative")
