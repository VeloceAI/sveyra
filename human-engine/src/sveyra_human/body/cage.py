"""Low-resolution deformation cage.

The cage is the thing the optimiser will move in Phase 3. It is a stack of
cross-section rings per body part, a few hundred vertices in total, rather than
the tens of thousands in the visible surface. Fitting a person means solving for
body parameters that produce a cage, never for individual surface vertices.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from sveyra_human.body.cross_sections import CrossSection, resample, torso_profile
from sveyra_human.body.parameters import BodyParameters

# Kept small on purpose: the cage is a control structure, not a render target.
TORSO_LEVELS = 14
TORSO_SEGMENTS = 16
LIMB_LEVELS = 6
LIMB_SEGMENTS = 10
HEAD_LEVELS = 8


@dataclass
class CagePart:
    """One stack of rings. rings[i] holds `segments` vertices in ring order."""

    name: str
    rings: np.ndarray  # (levels, segments, 3)
    closed_bottom: bool = False
    closed_top: bool = False

    @property
    def levels(self) -> int:
        return int(self.rings.shape[0])

    @property
    def segments(self) -> int:
        return int(self.rings.shape[1])


@dataclass
class BodyCage:
    parts: list[CagePart] = field(default_factory=list)

    @property
    def vertex_count(self) -> int:
        return sum(int(p.rings.shape[0] * p.rings.shape[1]) for p in self.parts)

    def part(self, name: str) -> CagePart:
        for p in self.parts:
            if p.name == name:
                return p
        raise KeyError(name)


def _stack(sections: list[CrossSection], segments: int) -> np.ndarray:
    return np.stack([s.outline(segments) for s in sections], axis=0)


def _tapered_limb(
    start: np.ndarray,
    end: np.ndarray,
    radius_start: float,
    radius_end: float,
    levels: int,
    segments: int,
) -> np.ndarray:
    """Rings swept along an arbitrary axis, tapering linearly.

    Used for arms and legs, where a swept capsule is a truthful enough shape at
    V1 and costs almost nothing to evaluate.
    """
    axis = end - start
    length = float(np.linalg.norm(axis))
    if length <= 0:
        raise ValueError("limb needs non-zero length")
    axis = axis / length

    # Any vector not parallel to the axis gives a stable frame.
    reference = np.array([0.0, 0.0, 1.0])
    if abs(float(np.dot(reference, axis))) > 0.9:
        reference = np.array([1.0, 0.0, 0.0])
    u = np.cross(axis, reference)
    u /= np.linalg.norm(u)
    # v = u x axis, not axis x u. Torso rings are built as (cos*X, sin*Z)
    # ascending in +Y, and cross(X, Z) = -Y, so the torso frame is left-handed
    # with respect to its own ascent axis. A limb built right-handed winds the
    # opposite way, which flips its triangles and points every limb normal
    # inward. Matching the handedness keeps one consistent outward surface.
    v = np.cross(u, axis)

    t = np.linspace(0.0, 1.0, levels)
    angles = np.linspace(0.0, 2.0 * np.pi, segments, endpoint=False)
    rings = np.empty((levels, segments, 3))
    for i, ti in enumerate(t):
        centre = start + axis * (length * ti)
        radius = radius_start + (radius_end - radius_start) * ti
        rings[i] = centre + radius * (
            np.outer(np.cos(angles), u) + np.outer(np.sin(angles), v)
        )
    return rings


def build_cage(params: BodyParameters, skeleton_positions: dict[str, np.ndarray]) -> BodyCage:
    """Assemble the full-body cage in the rest pose."""
    parts: list[CagePart] = []

    torso = resample(torso_profile(params), TORSO_LEVELS)
    parts.append(
        CagePart("torso", _stack(torso, TORSO_SEGMENTS), closed_bottom=True, closed_top=False)
    )

    # The crown defines standing height, so the head is anchored downward from
    # params.height rather than stacked upward from the neck. Stacking made the
    # mesh overshoot the height it was asked for.
    crown = float(params.height)
    neck_top = params.level_cm("neck") + float(params.neck_length)
    span = crown - neck_top
    if span <= 0:
        raise ValueError("neck reaches above the crown; check neck_length")
    head_sections = [
        CrossSection(params.level_cm("neck"), float(params.neck_width), float(params.neck_width)),
        CrossSection(neck_top, float(params.head_width) * 0.70, float(params.head_depth) * 0.72),
        CrossSection(
            neck_top + span * 0.40,
            float(params.head_width),
            float(params.head_depth),
        ),
        CrossSection(
            neck_top + span * 0.78,
            float(params.head_width) * 0.80,
            float(params.head_depth) * 0.84,
        ),
        CrossSection(
            crown,
            float(params.head_width) * 0.30,
            float(params.head_depth) * 0.32,
        ),
    ]
    parts.append(
        CagePart(
            "head",
            _stack(resample(head_sections, HEAD_LEVELS), TORSO_SEGMENTS),
            closed_bottom=False,
            closed_top=True,
        )
    )

    for side in ("L", "R"):
        parts.append(
            CagePart(
                f"upperarm_{side}",
                _tapered_limb(
                    skeleton_positions[f"upperarm_{side}"],
                    skeleton_positions[f"forearm_{side}"],
                    float(params.upper_arm_radius),
                    float(params.upper_arm_radius) * 0.82,
                    LIMB_LEVELS,
                    LIMB_SEGMENTS,
                ),
                closed_bottom=True,
            )
        )
        parts.append(
            CagePart(
                f"forearm_{side}",
                _tapered_limb(
                    skeleton_positions[f"forearm_{side}"],
                    skeleton_positions[f"hand_{side}"],
                    float(params.forearm_radius),
                    float(params.forearm_radius) * 0.66,
                    LIMB_LEVELS,
                    LIMB_SEGMENTS,
                ),
                closed_top=True,
            )
        )
        parts.append(
            CagePart(
                f"thigh_{side}",
                _tapered_limb(
                    skeleton_positions[f"thigh_{side}"],
                    skeleton_positions[f"calf_{side}"],
                    float(params.thigh_width) / 2.0,
                    float(params.calf_width) / 2.0 * 1.15,
                    LIMB_LEVELS,
                    LIMB_SEGMENTS,
                ),
                closed_bottom=True,
            )
        )
        parts.append(
            CagePart(
                f"calf_{side}",
                _tapered_limb(
                    skeleton_positions[f"calf_{side}"],
                    skeleton_positions[f"foot_{side}"],
                    float(params.calf_width) / 2.0,
                    float(params.ankle_width) / 2.0,
                    LIMB_LEVELS,
                    LIMB_SEGMENTS,
                ),
                closed_top=False,
            )
        )
        ankle = skeleton_positions[f"foot_{side}"]
        # A foot is a wedge from the ankle to the floor, projecting forward in
        # +Z. Crude, but it puts the body on the ground so that standing height
        # and inseam mean what they say.
        # Lift the toe centre by its own radius so the sole grazes y=0 instead of
        # sinking through it; the mesh must stand on the floor, not in it.
        toe_radius = float(params.ankle_width) / 2.2
        toe = np.array(
            [ankle[0], toe_radius, ankle[2] + float(params.ankle_width) * 2.6]
        )
        parts.append(
            CagePart(
                f"foot_{side}",
                _tapered_limb(
                    ankle,
                    toe,
                    float(params.ankle_width) / 2.0,
                    toe_radius,
                    4,
                    LIMB_SEGMENTS,
                ),
                closed_bottom=True,
                closed_top=True,
            )
        )

    return BodyCage(parts=parts)
