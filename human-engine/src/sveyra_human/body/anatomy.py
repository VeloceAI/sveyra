"""Derived measurements and collision volumes.

Girths come from the fitted cross sections rather than from a lookup table, so
a measurement always describes the geometry that was actually built.
"""

from __future__ import annotations

import numpy as np

from sveyra_human.body.cross_sections import CrossSection, torso_profile
from sveyra_human.body.parameters import BodyParameters


def section_girth(section: CrossSection, samples: int = 256) -> float:
    """Perimeter of a cross section, by summing its outline.

    A superellipse has no closed-form perimeter, so this integrates numerically.
    256 samples converges well below measuring-tape precision.
    """
    outline = section.outline(samples)
    closed = np.vstack([outline, outline[:1]])
    return float(np.linalg.norm(np.diff(closed, axis=0), axis=1).sum())


def measurements(params: BodyParameters) -> dict[str, float]:
    """Tape-style measurements in centimetres."""
    profile = {s.y: s for s in torso_profile(params)}
    by_level = {
        "chest": params.level_cm("chest"),
        "waist": params.level_cm("waist"),
        "hip": params.level_cm("hip"),
    }

    out: dict[str, float] = {
        "height_cm": round(float(params.height), 2),
        "shoulder_width_cm": round(float(params.shoulder_width), 2),
        "inseam_cm": round(params.level_cm("hip") - params.level_cm("ankle"), 2),
        "arm_length_cm": round(
            float(params.upper_arm_length) + float(params.forearm_length), 2
        ),
        "torso_length_cm": round(params.level_cm("neck") - params.level_cm("hip"), 2),
    }
    for name, level in by_level.items():
        section = profile.get(level)
        if section is not None:
            out[f"{name}_girth_cm"] = round(section_girth(section), 2)
    return out


def collision_primitives(
    params: BodyParameters, skeleton_positions: dict[str, np.ndarray]
) -> list[dict[str, object]]:
    """Cheap capsules for garment collision.

    Deliberately separate from the visible mesh: clothing should collide against
    a few dozen primitives, never against every skin triangle.
    """
    segments = [
        ("torso", "pelvis", "chest", float(params.chest_width) / 2.0),
        ("neck", "chest", "head", float(params.neck_width) / 2.0),
    ]
    for side in ("L", "R"):
        segments += [
            (f"upperarm_{side}", f"upperarm_{side}", f"forearm_{side}",
             float(params.upper_arm_radius)),
            (f"forearm_{side}", f"forearm_{side}", f"hand_{side}",
             float(params.forearm_radius)),
            (f"thigh_{side}", f"thigh_{side}", f"calf_{side}",
             float(params.thigh_width) / 2.0),
            (f"calf_{side}", f"calf_{side}", f"foot_{side}",
             float(params.calf_width) / 2.0),
        ]

    return [
        {
            "name": name,
            "kind": "capsule",
            "start": [round(float(v), 4) for v in skeleton_positions[a]],
            "end": [round(float(v), 4) for v in skeleton_positions[b]],
            "radius": round(radius, 4),
        }
        for name, a, b, radius in segments
    ]
