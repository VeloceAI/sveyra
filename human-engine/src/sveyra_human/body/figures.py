"""Figure types: an adult man, an adult woman, a child.

mannequin.js draws its three figures from one body with a `feminine` flag and a
height, and that is the right shape for the idea: the difference between these
bodies is proportion, not a different model.

What it does not do is change proportion with age, and that is the difference a
child actually reads by. A child is not a short adult. Adults stand about seven
and a half head-heights tall and a small child about five, so the head fraction
moves further than anything else here, and the limbs move against it.

Figures are a starting point for someone who has given us nothing but a height
and a choice. A body measured from photographs overrides all of this.
"""

from __future__ import annotations

from dataclasses import dataclass

from sveyra_human.body.parameters import BodyParameters
from sveyra_human.body.proportions import _ANTHROPOMETRIC

# Fractions of standing height, as overrides on the neutral adult table.
FIGURES: dict[str, dict[str, float]] = {
    "man": {
        "shoulder_width": 0.259,
        "shoulder_depth": 0.112,
        "chest_width": 0.200,
        "chest_depth": 0.118,
        "waist_width": 0.158,
        "waist_depth": 0.104,
        "hip_width": 0.185,
        "hip_depth": 0.122,
        "neck_width": 0.075,
        "upper_arm_radius": 0.037,
        "thigh_width": 0.100,
    },
    "woman": {
        "shoulder_width": 0.230,
        "shoulder_depth": 0.100,
        "chest_width": 0.183,
        # Deeper than the man's through the bust while narrower across it.
        "chest_depth": 0.132,
        "waist_width": 0.143,
        "waist_depth": 0.098,
        "hip_width": 0.207,
        "hip_depth": 0.133,
        "neck_width": 0.064,
        "upper_arm_radius": 0.032,
        "thigh_width": 0.103,
    },
    "child": {
        # The head is the whole tell. At five head-heights this is 0.165 of
        # standing height against an adult's 0.130.
        "head_height": 0.165,
        "head_width": 0.115,
        "head_depth": 0.140,
        "neck_length": 0.040,
        "neck_width": 0.062,
        "shoulder_width": 0.222,
        "shoulder_depth": 0.092,
        "chest_width": 0.170,
        "chest_depth": 0.105,
        "waist_width": 0.152,
        "waist_depth": 0.100,
        "hip_width": 0.170,
        "hip_depth": 0.110,
        # Limbs are shorter against height, which is the other half of why a
        # child scaled up does not look like an adult.
        "upper_arm_length": 0.158,
        "forearm_length": 0.142,
        "thigh_length": 0.222,
        "calf_length": 0.228,
        "upper_arm_radius": 0.030,
        "forearm_radius": 0.024,
        "thigh_width": 0.086,
        "calf_width": 0.060,
    },
}

DEFAULT_HEIGHT_CM = {"man": 178.0, "woman": 165.0, "child": 115.0}


@dataclass
class FigureProportions:
    """A `ProportionsSource` for one of the figure types."""

    kind: str = "man"

    @property
    def name(self) -> str:
        return f"figure:{self.kind}"

    def fractions(self, height_cm: float, weight_kg: float | None = None) -> dict[str, float]:
        if self.kind not in FIGURES:
            raise ValueError(f"unknown figure {self.kind!r}; expected one of {sorted(FIGURES)}")
        out = dict(_ANTHROPOMETRIC)
        out.update(FIGURES[self.kind])
        return out


def figure(kind: str, height_cm: float | None = None) -> BodyParameters:
    """Build a body of one figure type, at its own typical height by default."""
    if kind not in FIGURES:
        raise ValueError(f"unknown figure {kind!r}; expected one of {sorted(FIGURES)}")
    return BodyParameters(
        height=height_cm if height_cm is not None else DEFAULT_HEIGHT_CM[kind],
        proportions=FigureProportions(kind),
    )
