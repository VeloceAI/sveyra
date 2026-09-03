"""Skeleton in the form a renderer needs.

The engine's skeleton is world-space joint positions. glTF wants a node
hierarchy with local transforms and inverse bind matrices, so the conversion
lives here rather than leaking into either side.
"""

from __future__ import annotations

import numpy as np

from sveyra_human.rig.weights import DEFORMING_BONES
from sveyra_human.skeleton.joints import HIERARCHY
from sveyra_human.skeleton.model import Skeleton

CM_TO_M = 0.01


def joint_order() -> list[str]:
    """Bones in binding order, parents before children."""
    return list(DEFORMING_BONES)


def local_translations(skeleton: Skeleton, order: list[str]) -> dict[str, np.ndarray]:
    """Each joint's offset from its parent, in metres.

    Joints whose parent is outside the deforming set are measured from the
    nearest ancestor that is inside it, so the chain stays connected.
    """
    present = set(order)
    out: dict[str, np.ndarray] = {}
    for name in order:
        parent = HIERARCHY.get(name)
        while parent is not None and parent not in present:
            parent = HIERARCHY.get(parent)
        origin = skeleton.positions[parent] if parent else np.zeros(3)
        out[name] = (skeleton.positions[name] - origin) * CM_TO_M
    return out


def effective_parent(name: str, order: list[str]) -> str | None:
    present = set(order)
    parent = HIERARCHY.get(name)
    while parent is not None and parent not in present:
        parent = HIERARCHY.get(parent)
    return parent


def inverse_bind_matrices(skeleton: Skeleton, order: list[str]) -> np.ndarray:
    """One 4x4 per joint, moving a vertex from model space into joint space.

    The rest pose has no rotation, so each is a pure inverse translation.
    """
    matrices = np.tile(np.eye(4, dtype=np.float32), (len(order), 1, 1))
    for i, name in enumerate(order):
        matrices[i, :3, 3] = -(skeleton.positions[name] * CM_TO_M)
    return matrices
