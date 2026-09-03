"""Objective terms.

Each term is a small object that turns a candidate body into residuals. Keeping
them separate is deliberate: the total objective is a weighted sum, and the only
way to tell which part of a fit is fighting which is to be able to evaluate,
weight and disable them one at a time.

Residuals, not scalar costs, because `least_squares` exploits the structure.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

from sveyra_human.body.parameters import BodyParameters


class ObjectiveTerm(Protocol):
    name: str
    weight: float

    def residuals(self, params: BodyParameters) -> np.ndarray:
        """Return residuals, already scaled by weight."""
        ...


@dataclass
class ProportionPrior:
    """Pulls a body back toward plausible proportions for its height.

    Silhouettes underdetermine a body: a wide shallow torso and a narrow deep
    one can project identically in one view. Without a prior the solver drifts
    into shapes that match the pixels and are not human.
    """

    name: str = "proportion"
    weight: float = 0.35
    tolerance: float = 0.45  # fractional deviation tolerated before it bites

    def residuals(self, params: BodyParameters) -> np.ndarray:
        neutral = BodyParameters(height=params.height)
        out: list[float] = []
        for field in (
            "chest_width",
            "chest_depth",
            "waist_width",
            "waist_depth",
            "hip_width",
            "hip_depth",
        ):
            expected = float(getattr(neutral, field))
            actual = float(getattr(params, field))
            deviation = (actual - expected) / expected
            # Free inside the tolerance band, linear outside it.
            excess = max(0.0, abs(deviation) - self.tolerance)
            out.append(np.sign(deviation) * excess * expected)
        return self.weight * np.array(out)


@dataclass
class AnatomicalPrior:
    """Orderings that hold for essentially every human body.

    A waist narrower than the chest and hips is not a statistical preference,
    it is what a torso is. Encoding it as a one-sided penalty keeps the solver
    out of shapes no photograph could actually show.
    """

    name: str = "anatomical"
    weight: float = 0.6

    def residuals(self, params: BodyParameters) -> np.ndarray:
        chest_w = float(params.chest_width)
        waist_w = float(params.waist_width)
        hip_w = float(params.hip_width)
        chest_d = float(params.chest_depth)
        waist_d = float(params.waist_depth)

        return self.weight * np.array(
            [
                # Torsos are wider than they are deep.
                max(0.0, chest_d - chest_w),
                max(0.0, waist_d - waist_w),
                # A waist wider than both chest and hips is not a waist.
                max(0.0, waist_w - max(chest_w, hip_w) * 1.15),
            ]
        )


@dataclass
class SmoothnessTerm:
    """Discourages a torso that steps between neighbouring cross sections."""

    name: str = "smoothness"
    weight: float = 0.15

    def residuals(self, params: BodyParameters) -> np.ndarray:
        widths = np.array(
            [float(params.hip_width), float(params.waist_width), float(params.chest_width)]
        )
        depths = np.array(
            [float(params.hip_depth), float(params.waist_depth), float(params.chest_depth)]
        )
        return self.weight * np.concatenate([np.diff(widths, 2), np.diff(depths, 2)])


def default_terms() -> list[ObjectiveTerm]:
    return [ProportionPrior(), AnatomicalPrior(), SmoothnessTerm()]


def prior_residuals(params: BodyParameters, terms: list[ObjectiveTerm]) -> np.ndarray:
    if not terms:
        return np.zeros(0)
    return np.concatenate([term.residuals(params) for term in terms])
