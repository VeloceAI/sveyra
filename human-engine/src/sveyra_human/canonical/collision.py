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
    "wrist",
    "upperleg02",
    "lowerleg",
    "foot",
)


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


def body_volumes(body: CanonicalBodyMesh, rig: CanonicalRig) -> dict[str, list[Capsule]]:
    """The trunk a limb must stay out of, and the limbs that must stay out."""
    return {
        "trunk": build_capsules(body, rig, TRUNK_PREFIXES),
        "limb": build_capsules(body, rig, LIMB_PREFIXES),
    }


def segment_distance(
    a0: np.ndarray, a1: np.ndarray, b0: np.ndarray, b1: np.ndarray
) -> float:
    """Closest distance between two segments.

    Sampled rather than solved. The exact form has four degenerate cases and
    this is called on a handful of capsules, so the arithmetic is not worth the
    edge cases it would bring with it.
    """
    steps = np.linspace(0.0, 1.0, 12)[:, None]
    pa = a0 + steps * (a1 - a0)
    pb = b0 + steps * (b1 - b0)
    return float(np.min(np.linalg.norm(pa[:, None, :] - pb[None, :, :], axis=2)))


def penetration_cm(limb: Capsule, trunk: Capsule) -> float:
    """How far one capsule is inside another; zero when they are clear."""
    gap = segment_distance(limb.head_cm, limb.tail_cm, trunk.head_cm, trunk.tail_cm)
    overlap = (limb.radius_cm + trunk.radius_cm) - gap
    return float(max(0.0, overlap))
