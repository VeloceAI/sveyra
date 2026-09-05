"""Landmarks to joint rotations.

The method is MakeHuman.js's `BlazePoseConverter`: a bone's direction is the
vector between two landmarks, and a second landmark pair pins the roll about
that direction. What differs here is the frame. MakeHuman.js aligns to an
absolute convention and then corrects with hand-tuned ninety-degree rotations
per bone; this solves for the rotation carrying our own rest bone onto the
observed one, so there is nothing to hand-tune and nothing to re-tune when the
rest pose changes.

A bone direction cannot say how a limb is twisted about its own length. Where a
second landmark pair is available the roll is solved; everywhere else the
minimal rotation is used and the twist stays zero. That is a stated limit, not
a silent guess.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from sveyra_human.pose.landmarks import Landmarks
from sveyra_human.skeleton.joints import HIERARCHY
from sveyra_human.skeleton.limits import (
    HINGES,
    LIMITS,
    clamp_pose,
    impossible_joints,
)
from sveyra_human.skeleton.model import Skeleton


@dataclass(frozen=True)
class BoneObservation:
    """Which landmarks describe one bone.

    `head` and `tail` give the direction; naming two landmarks for either takes
    their midpoint, which is how the torso gets an axis when no single landmark
    sits on the spine. `roll` names a left-to-right pair that pins rotation
    about that direction.
    """

    head: tuple[str, ...]
    tail: tuple[str, ...]
    roll: tuple[str, str] | None = None

    def required(self) -> tuple[str, ...]:
        return self.head + self.tail + (self.roll or ())


def _bone(head: str | tuple, tail: str | tuple, roll: tuple | None = None):
    as_tuple = lambda v: (v,) if isinstance(v, str) else tuple(v)  # noqa: E731
    return BoneObservation(as_tuple(head), as_tuple(tail), roll)


# Only bones a camera can actually see, each observed along its own axis. The
# clavicles and the spine subdivisions carry no landmark and stay at rest; so do
# the hands and feet, which are leaves in this rig and so have no direction to
# solve for.
OBSERVED: dict[str, BoneObservation] = {
    # The torso's axis is hip centre to shoulder centre, and the hip line says
    # which way it faces. This one bone carries the whole trunk.
    "pelvis": _bone(
        ("left_hip", "right_hip"),
        ("left_shoulder", "right_shoulder"),
        ("left_hip", "right_hip"),
    ),
    "neck": _bone(
        ("left_shoulder", "right_shoulder"),
        ("left_ear", "right_ear"),
        ("left_ear", "right_ear"),
    ),
    "upperarm_L": _bone("left_shoulder", "left_elbow"),
    "forearm_L": _bone("left_elbow", "left_wrist"),
    "upperarm_R": _bone("right_shoulder", "right_elbow"),
    "forearm_R": _bone("right_elbow", "right_wrist"),
    "thigh_L": _bone("left_hip", "left_knee"),
    "calf_L": _bone("left_knee", "left_ankle"),
    "thigh_R": _bone("right_hip", "right_knee"),
    "calf_R": _bone("right_knee", "right_ankle"),
}


@dataclass
class SolvedPose:
    """Rotations in radians per joint, plus an account of what could not be read."""

    rotations: dict[str, tuple[float, float, float]]
    solved: list[str] = field(default_factory=list)
    unseen: list[str] = field(default_factory=list)
    clamped: list[str] = field(default_factory=list)

    @property
    def coverage(self) -> float:
        total = len(self.solved) + len(self.unseen)
        return len(self.solved) / total if total else 0.0

    def to_dict(self) -> dict[str, object]:
        return {
            "rotations": {
                k: [round(v, 5) for v in r] for k, r in self.rotations.items()
            },
            "solved": sorted(self.solved),
            "unseen": sorted(self.unseen),
            "clamped": sorted(self.clamped),
            "coverage": round(self.coverage, 3),
        }


def _centre(landmarks: Landmarks, names: tuple[str, ...]) -> np.ndarray:
    return np.mean([landmarks.get(n) for n in names], axis=0)


def _unit(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-9 else np.array([0.0, 1.0, 0.0])


def _frame(primary: np.ndarray, reference: np.ndarray) -> np.ndarray:
    """An orthonormal basis whose first column is `primary`."""
    x = _unit(primary)
    z = np.cross(x, reference)
    if float(np.linalg.norm(z)) < 1e-9:
        fallback = [1.0, 0.0, 0.0] if abs(x[0]) < 0.9 else [0.0, 0.0, 1.0]
        z = np.cross(x, np.array(fallback))
    z = _unit(z)
    return np.column_stack([x, np.cross(z, x), z])


def _minimal_rotation(rest: np.ndarray, observed: np.ndarray) -> np.ndarray:
    """The smallest rotation carrying one direction onto another.

    Building a basis for each direction and composing them would be the obvious
    alternative, but with no reference vector each basis has to invent its own
    second axis, and the two can invent differently for directions that are
    almost the same. That shows up as a limb snapping into a wrong twist. This
    has no such freedom: it rotates in the single plane the two directions span.
    """
    a, b = _unit(rest), _unit(observed)
    v = np.cross(a, b)
    s = float(np.linalg.norm(v))
    c = float(np.dot(a, b))
    if s < 1e-9:
        if c > 0:
            return np.eye(3)
        seed = np.array([1.0, 0.0, 0.0]) if abs(a[0]) < 0.9 else np.array([0.0, 0.0, 1.0])
        axis = _unit(np.cross(a, seed))
        outer = np.outer(axis, axis)
        return 2.0 * outer - np.eye(3)
    k = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + k + k @ k * ((1.0 - c) / (s * s))


def _hinge_rotation(rest: np.ndarray, observed: np.ndarray, index: int) -> np.ndarray:
    """A bend about the flex axis alone, which is what makes a hinge a hinge.

    Solving a hinge as a free rotation lets it reach an impossible direction by
    pairing a legal bend with a half turn of twist, and the joint limits never
    see it. Restricting the solve to the one axis is what makes clamping mean
    something for an elbow or a knee.
    """
    axis = np.zeros(3)
    axis[index] = 1.0
    flat_rest = _unit(rest - axis * float(np.dot(rest, axis)))
    flat_obs = observed - axis * float(np.dot(observed, axis))
    if float(np.linalg.norm(flat_obs)) < 1e-9:
        return np.eye(3)
    flat_obs = _unit(flat_obs)
    angle = float(
        np.arctan2(float(np.dot(np.cross(flat_rest, flat_obs), axis)),
                   float(np.dot(flat_rest, flat_obs)))
    )
    c, s = np.cos(angle), np.sin(angle)
    # Cyclic order, not ascending: about Y the pair runs Z then X. Taking them
    # in ascending order builds the mirror of the intended rotation, and a bend
    # comes back as its own negation.
    a, b = (index + 1) % 3, (index + 2) % 3
    m = np.eye(3)
    m[a, a] = m[b, b] = c
    m[a, b] = -s
    m[b, a] = s
    return m


def _to_euler_xyz(m: np.ndarray) -> tuple[float, float, float]:
    """Matrix to intrinsic XYZ Euler angles, the order the rig and viewer use."""
    sy = float(np.clip(-m[2, 0], -1.0, 1.0))
    y = float(np.arcsin(sy))
    if abs(sy) < 0.99999:
        x = float(np.arctan2(m[2, 1], m[2, 2]))
        z = float(np.arctan2(m[1, 0], m[0, 0]))
    else:
        # Gimbal lock: roll and yaw become the same motion, so put it all in one.
        x = float(np.arctan2(-m[1, 2], m[1, 1]))
        z = 0.0
    return (x, y, z)


def _rest_direction(joint: str, skeleton: Skeleton) -> np.ndarray | None:
    """Which way this bone points at rest, toward its first child."""
    children = [n for n, p in HIERARCHY.items() if p == joint]
    if not children or joint not in skeleton.positions:
        return None
    child = children[0]
    if child not in skeleton.positions:
        return None
    direction = skeleton.positions[child] - skeleton.positions[joint]
    return direction if float(np.linalg.norm(direction)) > 1e-6 else None


def solve_pose(landmarks: Landmarks, skeleton: Skeleton) -> SolvedPose:
    """Recover joint rotations from detected landmarks.

    Solved parent-first: a child's observed direction only means something once
    the parent's rotation is known, because that is the frame it lives in.
    """
    rotations: dict[str, tuple[float, float, float]] = {}
    world: dict[str, np.ndarray] = {"root": np.eye(3)}
    solved: list[str] = []
    unseen: list[str] = []

    for joint, parent in HIERARCHY.items():
        if parent is None:
            continue
        parent_world = world.get(parent, np.eye(3))

        bone = OBSERVED.get(joint)
        rest_child = _rest_direction(joint, skeleton)
        if bone is None or rest_child is None or not landmarks.seen(*bone.required()):
            if bone is not None:
                unseen.append(joint)
            world[joint] = parent_world
            continue

        observed = _centre(landmarks, bone.tail) - _centre(landmarks, bone.head)
        rest_ref = observed_ref = None
        if bone.roll is not None:
            left, right = bone.roll
            observed_ref = landmarks.get(right) - landmarks.get(left)
            # The rig puts the subject's left at +X, so a line running from
            # their left landmark to their right points along -X at rest.
            rest_ref = np.array([-1.0, 0.0, 0.0])

        # Into the parent's frame: a child's rotation is relative to it.
        local_obs = parent_world.T @ observed
        local_ref = parent_world.T @ observed_ref if observed_ref is not None else None

        if joint in HINGES:
            local = _hinge_rotation(rest_child, local_obs, LIMITS[joint].axes[0])
        elif local_ref is not None and rest_ref is not None:
            local = _frame(local_obs, local_ref) @ _frame(rest_child, rest_ref).T
        else:
            local = _minimal_rotation(rest_child, local_obs)
        rotations[joint] = _to_euler_xyz(local)
        world[joint] = parent_world @ local
        solved.append(joint)

    return SolvedPose(
        rotations=clamp_pose(rotations),
        solved=solved,
        unseen=unseen,
        clamped=impossible_joints(rotations),
    )
