"""The SVEYRA skeleton definition.

Deliberately our own hierarchy rather than SMPL's, so nothing in the engine
inherits a research-only licence. See THIRD_PARTY.md.
"""

from __future__ import annotations

ROOT = "root"

# child -> parent. Order matters: parents appear before their children.
HIERARCHY: dict[str, str | None] = {
    "root": None,
    "pelvis": "root",
    "spine_1": "pelvis",
    "spine_2": "spine_1",
    "chest": "spine_2",
    "neck": "chest",
    "head": "neck",
    "clavicle_L": "chest",
    "upperarm_L": "clavicle_L",
    "forearm_L": "upperarm_L",
    "hand_L": "forearm_L",
    "clavicle_R": "chest",
    "upperarm_R": "clavicle_R",
    "forearm_R": "upperarm_R",
    "hand_R": "forearm_R",
    "thigh_L": "pelvis",
    "calf_L": "thigh_L",
    "foot_L": "calf_L",
    "thigh_R": "pelvis",
    "calf_R": "thigh_R",
    "foot_R": "calf_R",
}

JOINT_NAMES: tuple[str, ...] = tuple(HIERARCHY)


def children_of(joint: str) -> list[str]:
    return [name for name, parent in HIERARCHY.items() if parent == joint]


def is_valid_hierarchy() -> bool:
    """Every parent must exist and precede its child, and only root is orphaned."""
    seen: set[str] = set()
    for name, parent in HIERARCHY.items():
        if parent is None:
            if name != ROOT:
                return False
        elif parent not in seen:
            return False
        seen.add(name)
    return True
