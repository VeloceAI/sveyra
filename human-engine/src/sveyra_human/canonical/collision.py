"""Rigid volumes approximating the body, for keeping limbs out of it.

A pose can put every joint inside its clinical range and still drive an arm
through the ribs, because a range says what one joint may do and nothing about
where the rest of the body is. This fits a capsule to each bone from the mesh
itself, so the volumes follow whatever body was built rather than describing a
generic one.

They are wanted twice over. A viewer uses them to refuse a pose that puts a limb
inside the trunk. Reconstruction wants them for the same reason from the other
direction: a pose recovered from a photograph is a guess, and a guess that puts
an elbow inside the chest is one the solver should be able to reject.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from sveyra_human.canonical.body import CanonicalBodyMesh
from sveyra_human.canonical.rig import CanonicalRig

# A capsule takes the radius that covers most of its bone's flesh, not all of
# it. The furthest vertex on an upper arm is at the shoulder, where the deltoid
# swells into the torso, and letting that set the radius makes an arm that
# cannot come near the body at all.
RADIUS_PERCENTILE = 82.0

# The hand is fitted as one rigid proxy on the wrist.  Finger capsules fitted
# independently are a poor approximation: skin weights around the palm are
# deliberately shared by several finger bones, which makes every individual
# radius much too large.  A principal-axis capsule follows the whole measured
# hand closely and is sufficient until articulated-finger collision is added.
HAND_RADIUS_PERCENTILE = 90.0
HAND_AXIS_PERCENTILES = (5.0, 95.0)

# Bones too small to be worth a volume of their own; their flesh belongs to the
# parent capsule.
MIN_LENGTH_CM = 4.0

# Which capsules the body is made of, and which are limbs that must stay out.
TRUNK_PREFIXES = ("spine", "pelvis", "neck", "head", "breast")

# Only the distal half of each limb is tested against the trunk. The proximal
# segment is the joint itself: a deltoid genuinely sits inside the torso's
# silhouette and a hip is inside the pelvis, so including them means the body is
# always colliding with itself and a neutral stand gets held back.
LIMB_PREFIXES = (
    "upperarm02",
    "lowerarm",
    "upperleg02",
    "lowerleg",
    "foot",
)

HAND_ROOTS = ("wrist.L", "wrist.R")


@dataclass(frozen=True)
class Capsule:
    """A segment with a radius: the volume within `radius` of the segment."""

    bone: str
    head_cm: np.ndarray
    tail_cm: np.ndarray
    radius_cm: float

    @property
    def length_cm(self) -> float:
        return float(np.linalg.norm(self.tail_cm - self.head_cm))

    def to_dict(self) -> dict[str, object]:
        return {
            "bone": self.bone,
            "head": [round(float(v), 5) for v in self.head_cm],
            "tail": [round(float(v), 5) for v in self.tail_cm],
            "radius": round(float(self.radius_cm), 5),
        }

    def to_bone_local_dict(self, bone_head_cm: np.ndarray) -> dict[str, object]:
        """Serialize endpoints in the transform space of ``bone``.

        Canonical rig coordinates are model-space at bind.  A runtime parents a
        capsule to its bone, so sending those coordinates unchanged translates
        the proxy twice and leaves the actual skin unprotected.
        """
        origin = np.asarray(bone_head_cm, dtype=float)
        return {
            "bone": self.bone,
            "space": "bone-local",
            "head": [round(float(v), 5) for v in self.head_cm - origin],
            "tail": [round(float(v), 5) for v in self.tail_cm - origin],
            "radius": round(float(self.radius_cm), 5),
        }


def _dominant_bone(rig: CanonicalRig) -> np.ndarray:
    """The bone carrying most of each vertex's weight."""
    return rig.joint_indices[np.arange(rig.weights.shape[0]), np.argmax(rig.weights, axis=1)]


def _distance_to_segment(points: np.ndarray, head: np.ndarray, tail: np.ndarray) -> np.ndarray:
    axis = tail - head
    length_sq = float(axis @ axis)
    if length_sq < 1e-9:
        return np.linalg.norm(points - head, axis=1)
    t = np.clip((points - head) @ axis / length_sq, 0.0, 1.0)
    nearest = head + t[:, None] * axis
    return np.linalg.norm(points - nearest, axis=1)


def build_capsules(
    body: CanonicalBodyMesh,
    rig: CanonicalRig,
    prefixes: tuple[str, ...] | None = None,
) -> list[Capsule]:
    """One capsule per bone, sized to the flesh that bone actually carries."""
    owner = _dominant_bone(rig)
    vertices = body.vertices_cm
    capsules: list[Capsule] = []

    for index, bone in enumerate(rig.bones):
        if prefixes is not None and not bone.name.startswith(prefixes):
            continue
        head = np.asarray(bone.head_cm, dtype=float)
        tail = np.asarray(bone.tail_cm, dtype=float)
        if float(np.linalg.norm(tail - head)) < MIN_LENGTH_CM:
            continue

        mine = vertices[owner == index]
        if mine.shape[0] < 8:
            continue
        radius = float(np.percentile(_distance_to_segment(mine, head, tail), RADIUS_PERCENTILE))
        if radius <= 0.0:
            continue
        capsules.append(Capsule(bone=bone.name, head_cm=head, tail_cm=tail, radius_cm=radius))

    return capsules


def _descendants(rig: CanonicalRig, root_index: int) -> set[int]:
    descendants = {root_index}
    for index, bone in enumerate(rig.bones):
        parent = bone.parent_index
        while parent is not None:
            if parent == root_index:
                descendants.add(index)
                break
            parent = rig.bones[parent].parent_index
    return descendants


def build_hand_capsules(body: CanonicalBodyMesh, rig: CanonicalRig) -> list[Capsule]:
    """Fit one measured palm-and-fingers capsule to each wrist transform."""
    owner = _dominant_bone(rig)
    vertices = body.vertices_cm
    by_name = {bone.name: index for index, bone in enumerate(rig.bones)}
    capsules: list[Capsule] = []

    for name in HAND_ROOTS:
        root_index = by_name.get(name)
        if root_index is None:
            continue
        indices = _descendants(rig, root_index)
        points = vertices[np.isin(owner, list(indices))]
        if points.shape[0] < 16:
            continue

        centre = points.mean(axis=0)
        covariance = np.cov(points - centre, rowvar=False)
        values, vectors = np.linalg.eigh(covariance)
        axis = vectors[:, int(np.argmax(values))]
        wrist = np.asarray(rig.bones[root_index].head_cm, dtype=float)
        if float(axis @ (centre - wrist)) < 0.0:
            axis = -axis

        projection = (points - centre) @ axis
        low, high = np.percentile(projection, HAND_AXIS_PERCENTILES)
        head = centre + axis * low
        tail = centre + axis * high
        radius = float(
            np.percentile(
                _distance_to_segment(points, head, tail),
                HAND_RADIUS_PERCENTILE,
            )
        )
        capsules.append(Capsule(bone=name, head_cm=head, tail_cm=tail, radius_cm=radius))

    return capsules


def body_volumes(body: CanonicalBodyMesh, rig: CanonicalRig) -> dict[str, list[Capsule]]:
    """The trunk a limb must stay out of, and the limbs that must stay out."""
    return {
        "trunk": build_capsules(body, rig, TRUNK_PREFIXES),
        "limb": build_capsules(body, rig, LIMB_PREFIXES) + build_hand_capsules(body, rig),
    }


def segment_distance(a0: np.ndarray, a1: np.ndarray, b0: np.ndarray, b1: np.ndarray) -> float:
    """Exact closest distance between two finite segments."""
    a0 = np.asarray(a0, dtype=float)
    a1 = np.asarray(a1, dtype=float)
    b0 = np.asarray(b0, dtype=float)
    b1 = np.asarray(b1, dtype=float)
    u = a1 - a0
    v = b1 - b0
    w = a0 - b0
    aa = float(u @ u)
    bb = float(u @ v)
    cc = float(v @ v)
    dd = float(u @ w)
    ee = float(v @ w)
    epsilon = 1e-12

    if aa <= epsilon and cc <= epsilon:
        return float(np.linalg.norm(w))
    if aa <= epsilon:
        t = float(np.clip(ee / cc, 0.0, 1.0))
        return float(np.linalg.norm(w - t * v))
    if cc <= epsilon:
        s = float(np.clip(-dd / aa, 0.0, 1.0))
        return float(np.linalg.norm(w + s * u))

    denominator = aa * cc - bb * bb
    s_numerator = 0.0
    s_denominator = denominator
    t_numerator = 0.0
    t_denominator = denominator

    if denominator <= epsilon:
        s_numerator = 0.0
        s_denominator = 1.0
        t_numerator = ee
        t_denominator = cc
    else:
        s_numerator = bb * ee - cc * dd
        t_numerator = aa * ee - bb * dd
        if s_numerator < 0.0:
            s_numerator = 0.0
            t_numerator = ee
            t_denominator = cc
        elif s_numerator > s_denominator:
            s_numerator = s_denominator
            t_numerator = ee + bb
            t_denominator = cc

    if t_numerator < 0.0:
        t_numerator = 0.0
        if -dd < 0.0:
            s_numerator = 0.0
        elif -dd > aa:
            s_numerator = s_denominator
        else:
            s_numerator = -dd
            s_denominator = aa
    elif t_numerator > t_denominator:
        t_numerator = t_denominator
        if -dd + bb < 0.0:
            s_numerator = 0.0
        elif -dd + bb > aa:
            s_numerator = s_denominator
        else:
            s_numerator = -dd + bb
            s_denominator = aa

    s = 0.0 if abs(s_numerator) <= epsilon else s_numerator / s_denominator
    t = 0.0 if abs(t_numerator) <= epsilon else t_numerator / t_denominator
    return float(np.linalg.norm(w + s * u - t * v))


def penetration_cm(limb: Capsule, trunk: Capsule) -> float:
    """How far one capsule is inside another; zero when they are clear."""
    gap = segment_distance(limb.head_cm, limb.tail_cm, trunk.head_cm, trunk.tail_cm)
    overlap = (limb.radius_cm + trunk.radius_cm) - gap
    return float(max(0.0, overlap))
