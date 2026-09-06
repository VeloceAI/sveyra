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

    Flexion is the bend, abduction is movement away from the body's midline,
    and twist is rotation about the limb's own length.

    Which Euler component carries which of those is not fixed. A rotation here
    is expressed in the parent's axes, and the rig has no per-bone local frame,
    so the answer depends on where the bone points at rest: twist is always
    about the bone's own direction. The legs hang down Y, so a knee bends about
    X; the T-pose arms lie along X, so an elbow bends about Y. `axes` records
    that per joint instead of letting every consumer assume the leg case.
    """

    flex: tuple[float, float]
    abduct: tuple[float, float]
    twist: tuple[float, float]
    axes: tuple[int, int, int] = (0, 2, 1)
    neutral: tuple[float, float, float] = (0.0, 0.0, 0.0)

    def ranges(self) -> tuple[tuple[float, float], ...]:
        """The (min, max) for each of x, y, z in that order."""
        out: list[tuple[float, float]] = [(0.0, 0.0)] * 3
        flex_axis, abduct_axis, twist_axis = self.axes
        out[flex_axis] = self.flex
        out[abduct_axis] = self.abduct
        out[twist_axis] = self.twist
        return tuple(
            (lo + self.neutral[i], hi + self.neutral[i])
            for i, (lo, hi) in enumerate(out)
        )

    def clamp(self, x: float, y: float, z: float) -> tuple[float, float, float]:
        return tuple(  # type: ignore[return-value]
            min(max(value, lo), hi)
            for value, (lo, hi) in zip((x, y, z), self.ranges())
        )

    def exceeds(self, x: float, y: float, z: float) -> bool:
        return (x, y, z) != self.clamp(x, y, z)


# Bone direction at rest to (flex, abduct, twist) Euler components. Twist is
# always the bone's own axis; abduction is the remaining one.
_AXES_ALONG_Y = (0, 2, 1)
_AXES_ALONG_X = (1, 2, 0)


def _limit(flex, abduct, twist, axes=_AXES_ALONG_Y, neutral=(0, 0, 0)) -> JointLimit:
    return JointLimit(
        flex=(radians(flex[0]), radians(flex[1])),
        abduct=(radians(abduct[0]), radians(abduct[1])),
        twist=(radians(twist[0]), radians(twist[1])),
        axes=axes,
        neutral=tuple(radians(v) for v in neutral),  # type: ignore[arg-type]
    )


# Anatomical neutral is standing with the arms at the sides, and every clinical
# range in this file is measured from there. The rig's rest is a T-pose, so for
# the shoulders the two differ by a right angle. Recording that offset is what
# lets an arm hang: without it, adducting to the side reads as ninety degrees of
# travel and gets clamped away long before the arm reaches the body.
_ARM_DOWN_L = (0, 0, -90)
_ARM_DOWN_R = (0, 0, 90)


# Hinges get no abduction and no twist at all: that is what makes them hinges.
LIMITS: dict[str, JointLimit] = {
    "pelvis": _limit((-25, 25), (-20, 20), (-30, 30)),
    "spine_1": _limit((-20, 25), (-18, 18), (-20, 20)),
    "spine_2": _limit((-20, 25), (-18, 18), (-20, 20)),
    "chest": _limit((-20, 25), (-18, 18), (-25, 25)),
    "neck": _limit((-30, 25), (-30, 30), (-45, 45)),
    "head": _limit((-40, 35), (-35, 35), (-55, 55)),
    "clavicle_L": _limit((-10, 10), (-15, 25), (-8, 8), _AXES_ALONG_X),
    "clavicle_R": _limit((-10, 10), (-25, 15), (-8, 8), _AXES_ALONG_X),
    # Shoulders are the freest joint in the body, and still not free.
    "upperarm_L": _limit(
        (-60, 150), (-45, 160), (-70, 70), _AXES_ALONG_X, _ARM_DOWN_L
    ),
    "upperarm_R": _limit(
        (-60, 150), (-160, 45), (-70, 70), _AXES_ALONG_X, _ARM_DOWN_R
    ),
    # Elbow: flexes to about 145 degrees, does not extend past straight.
    "forearm_L": _limit((-145, 0), (0, 0), (0, 0), _AXES_ALONG_X),
    "forearm_R": _limit((-145, 0), (0, 0), (0, 0), _AXES_ALONG_X),
    "hand_L": _limit((-70, 70), (-25, 30), (-80, 80), _AXES_ALONG_X),
    "hand_R": _limit((-70, 70), (-30, 25), (-80, 80), _AXES_ALONG_X),
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
            # By axis as well, so a client can clamp without having to know
            # which way this particular bone points at rest.
            "axis": [[round(lo, 4), round(hi, 4)] for lo, hi in limit.ranges()],
            "neutral": [round(v, 4) for v in limit.neutral],
            # Which Euler component carries flex, abduction and twist here.
            "axisOf": list(limit.axes),
        }
        for joint, limit in LIMITS.items()
    }
