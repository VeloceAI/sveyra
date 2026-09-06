"""Dual quaternion skinning.

Linear blend skinning collapses a joint under twist - the classic candy wrapper.
Dual quaternions preserve volume through a rotation, which matters most exactly
where clothing has to sit: shoulders, elbows, hips, knees.

Provided so posing can be evaluated on CPU for measurement and collision.
Renderers do their own skinning from the glTF weights.
"""

from __future__ import annotations

import numpy as np


def quaternion_from_axis_angle(axis: np.ndarray, radians: float) -> np.ndarray:
    """Unit quaternion as (w, x, y, z)."""
    norm = float(np.linalg.norm(axis))
    if norm < 1e-12:
        return np.array([1.0, 0.0, 0.0, 0.0])
    unit = np.asarray(axis, dtype=float) / norm
    half = radians / 2.0
    return np.concatenate([[np.cos(half)], unit * np.sin(half)])


def quaternion_multiply(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return np.array(
        [
            w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
            w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
        ]
    )


def dual_quaternion(rotation: np.ndarray, translation: np.ndarray) -> np.ndarray:
    """Pack a rotation and translation into (real, dual), each (w, x, y, z)."""
    real = np.asarray(rotation, dtype=float)
    t = np.concatenate([[0.0], np.asarray(translation, dtype=float)])
    dual = 0.5 * quaternion_multiply(t, real)
    return np.stack([real, dual])


def blend(dual_quats: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """Weighted blend of dual quaternions, then normalise.

    Signs are aligned to the first influence: quaternions double-cover
    rotations, so blending q with -q cancels instead of averaging.
    """
    reference = dual_quats[0, 0]
    signs = np.where(np.einsum("ij,j->i", dual_quats[:, 0], reference) < 0, -1.0, 1.0)
    aligned = dual_quats * signs[:, None, None]
    blended = np.einsum("i,ijk->jk", weights, aligned)
    norm = float(np.linalg.norm(blended[0]))
    if norm < 1e-12:
        return np.stack([np.array([1.0, 0.0, 0.0, 0.0]), np.zeros(4)])
    return blended / norm


def transform_point(dq: np.ndarray, point: np.ndarray) -> np.ndarray:
    real, dual = dq[0], dq[1]
    w, v = real[0], real[1:]
    rotated = point + 2.0 * np.cross(v, np.cross(v, point) + w * point)
    translation = 2.0 * (w * dual[1:] - dual[0] * v + np.cross(v, dual[1:]))
    return rotated + translation
