"""Skeleton instance: joint positions in world space, derived from body numbers.

Kept independent of the mesh. The rig binds one to the other later (Phase 7);
neither needs to know how the other is built.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from sveyra_human.body.parameters import BodyParameters
from sveyra_human.skeleton.joints import HIERARCHY, JOINT_NAMES


@dataclass(frozen=True)
class Skeleton:
    """World-space rest pose. Positions are centimetres, Y up, origin at the floor."""

    positions: dict[str, np.ndarray]

    def bone_length(self, joint: str) -> float:
        parent = HIERARCHY[joint]
        if parent is None:
            return 0.0
        return float(np.linalg.norm(self.positions[joint] - self.positions[parent]))

    def to_dict(self) -> dict[str, object]:
        return {
            "joints": {
                name: {
                    "position": [round(float(v), 4) for v in pos],
                    "parent": HIERARCHY[name],
                    "length_cm": round(self.bone_length(name), 4),
                }
                for name, pos in self.positions.items()
            }
        }


def build_skeleton(params: BodyParameters) -> Skeleton:
    """Place every joint from the body parameters, in a T-pose."""
    h = params.height
    lv = params.level_cm

    half_shoulder = float(params.shoulder_width) / 2.0
    half_hip = float(params.hip_width) / 2.0

    pelvis_y = lv("hip")
    chest_y = lv("chest")
    shoulder_y = lv("shoulder")
    neck_y = lv("neck")

    pos: dict[str, np.ndarray] = {
        "root": np.array([0.0, 0.0, 0.0]),
        "pelvis": np.array([0.0, pelvis_y, 0.0]),
        "spine_1": np.array([0.0, pelvis_y + (chest_y - pelvis_y) * 0.33, 0.0]),
        "spine_2": np.array([0.0, pelvis_y + (chest_y - pelvis_y) * 0.66, 0.0]),
        "chest": np.array([0.0, chest_y, 0.0]),
        "neck": np.array([0.0, neck_y, 0.0]),
        "head": np.array([0.0, neck_y + float(params.neck_length), 0.0]),
    }

    # Arms are laid out along X in the rest pose; the shoulder drops slightly
    # outboard by the slope parameter.
    #
    # Shoulder width is measured acromion to acromion, so the joint belongs
    # close to that bony point rather than tucked inside the chest. It was at
    # 0.39 to stop the arm reading as detached in a T-pose, where the arm
    # extends sideways and its root is hidden anyway. With the arms down that
    # same position buries the whole upper arm inside the chest, which is
    # narrower than the shoulders. The joint ball bridges what is left.
    torso_edge = float(params.shoulder_width) * 0.45
    for side, sign in (("L", 1.0), ("R", -1.0)):
        clav_x = sign * half_shoulder * 0.35
        arm_x = sign * torso_edge
        arm_y = shoulder_y - float(params.shoulder_slope)
        pos[f"clavicle_{side}"] = np.array([clav_x, shoulder_y, 0.0])
        pos[f"upperarm_{side}"] = np.array([arm_x, arm_y, 0.0])
        pos[f"forearm_{side}"] = np.array(
            [arm_x + sign * float(params.upper_arm_length), arm_y, 0.0]
        )
        pos[f"hand_{side}"] = np.array(
            [
                arm_x + sign * (float(params.upper_arm_length) + float(params.forearm_length)),
                arm_y,
                0.0,
            ]
        )

        leg_x = sign * half_hip * 0.5
        knee_y = lv("knee")
        ankle_y = lv("ankle")
        pos[f"thigh_{side}"] = np.array([leg_x, pelvis_y, 0.0])
        pos[f"calf_{side}"] = np.array([leg_x, knee_y, 0.0])
        pos[f"foot_{side}"] = np.array([leg_x, ankle_y, 0.0])

    missing = set(JOINT_NAMES) - set(pos)
    if missing:
        raise RuntimeError(f"skeleton is missing joints: {sorted(missing)}")
    _ = h
    return Skeleton(positions=pos)
