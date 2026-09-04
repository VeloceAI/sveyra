"""What a human joint can actually do.

An elbow is a hinge. It bends one way, stops at straight, and does not rotate
about its own long axis. Without that written down, a rig will happily fold a
forearm through an upper arm, which is the single fastest way to make an avatar
look wrong.

Ranges are radians in the joint's local frame, and are deliberately
conservative: they cover ordinary standing, walking and reaching, not gymnastics.
Figures are the usual clinical ranges of motion rounded to something a rig can
use, not measurements of any individual.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import radians


@dataclass(frozen=True)
class JointLimit:
    """Allowed rotation about each axis, as (minimum, maximum) radians.

    x is flexion and extension, the bend. z is abduction, moving away from the
    body's midline. y is twist about the limb's own length.
    """

    flex: tuple[float, float]
    abduct: tuple[float, float]
    twist: tuple[float, float]

    def clamp(self, x: float, y: float, z: float) -> tuple[float, float, float]:
        return (
            min(max(x, self.flex[0]), self.flex[1]),
            min(max(y, self.twist[0]), self.twist[1]),
            min(max(z, self.abduct[0]), self.abduct[1]),
        )

    def exceeds(self, x: float, y: float, z: float) -> bool:
        return (x, y, z) != self.clamp(x, y, z)


def _limit(flex, abduct, twist) -> JointLimit:
    return JointLimit(
        flex=(radians(flex[0]), radians(flex[1])),
        abduct=(radians(abduct[0]), radians(abduct[1])),
        twist=(radians(twist[0]), radians(twist[1])),
    )


# Hinges get no abduction and no twist at all: that is what makes them hinges.
LIMITS: dict[str, JointLimit] = {
    "pelvis": _limit((-25, 25), (-20, 20), (-30, 30)),
    "spine_1": _limit((-20, 25), (-18, 18), (-20, 20)),
    "spine_2": _limit((-20, 25), (-18, 18), (-20, 20)),
    "chest": _limit((-20, 25), (-18, 18), (-25, 25)),
    "neck": _limit((-30, 25), (-30, 30), (-45, 45)),
    "head": _limit((-40, 35), (-35, 35), (-55, 55)),
    "clavicle_L": _limit((-10, 10), (-15, 25), (-8, 8)),
    "clavicle_R": _limit((-10, 10), (-25, 15), (-8, 8)),
    # Shoulders are the freest joint in the body, and still not free.
    "upperarm_L": _limit((-60, 150), (-45, 160), (-70, 70)),
    "upperarm_R": _limit((-60, 150), (-160, 45), (-70, 70)),
    # Elbow: flexes to about 145 degrees, does not extend past straight.
    "forearm_L": _limit((-145, 0), (0, 0), (0, 0)),
    "forearm_R": _limit((-145, 0), (0, 0), (0, 0)),
    "hand_L": _limit((-70, 70), (-25, 30), (-80, 80)),
    "hand_R": _limit((-70, 70), (-30, 25), (-80, 80)),
    "thigh_L": _limit((-120, 25), (-30, 45), (-40, 40)),
    "thigh_R": _limit((-120, 25), (-45, 30), (-40, 40)),
    # Knee: flexes backward only, and locks straight.
    "calf_L": _limit((0, 140), (0, 0), (0, 0)),
    "calf_R": _limit((0, 140), (0, 0), (0, 0)),
    "foot_L": _limit((-45, 25), (-15, 15), (-10, 10)),
    "foot_R": _limit((-45, 25), (-15, 15), (-10, 10)),
}

# Joints with no rotation of their own; they exist to carry a transform.
FREE_JOINTS = frozenset({"root"})

HINGES = frozenset({"forearm_L", "forearm_R", "calf_L", "calf_R"})


def limit_for(joint: str) -> JointLimit | None:
    return LIMITS.get(joint)


def clamp_pose(
    pose: dict[str, tuple[float, float, float]],
) -> dict[str, tuple[float, float, float]]:
    """Bring a whole pose inside what a body can do.

    Unknown joints pass through: this constrains, it does not police the
    skeleton's contents.
    """
    out: dict[str, tuple[float, float, float]] = {}
    for joint, rotation in pose.items():
        limit = LIMITS.get(joint)
        out[joint] = limit.clamp(*rotation) if limit else rotation
    return out


def impossible_joints(pose: dict[str, tuple[float, float, float]]) -> list[str]:
    """Which joints in a pose a human could not reach."""
    return [
        joint
        for joint, rotation in pose.items()
        if (limit := LIMITS.get(joint)) is not None and limit.exceeds(*rotation)
    ]


def as_dict() -> dict[str, dict[str, list[float]]]:
    """Serialise for a viewer or a client that has to enforce the same rules."""
    return {
        joint: {
            "flex": [round(limit.flex[0], 4), round(limit.flex[1], 4)],
            "abduct": [round(limit.abduct[0], 4), round(limit.abduct[1], 4)],
            "twist": [round(limit.twist[0], 4), round(limit.twist[1], 4)],
        }
        for joint, limit in LIMITS.items()
    }
