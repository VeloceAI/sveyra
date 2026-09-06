"""Where a body's proportions come from.

The engine has always filled unset measurements from a table of fractions of
height. That table is a rule of thumb, not a model fitted to real bodies, and it
is the reason a fitted body can look proportioned rather than anatomical.

This makes the source swappable. The rule-of-thumb table is one implementation;
a mapping learned from scanned bodies is another, and dropping one in is a
constructor argument rather than an edit to `BodyParameters`.

Deliberately a port, because the obvious next implementation carries a licence
question. `zengyh1900/3D-Human-Body-Shape` is MIT and non-SMPL, which is rare
and useful, but it trains on the SPRING dataset, whose terms are separate from
the code's. Keeping the seam means that question can be answered without
unpicking anything.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

# Fractions of standing height for a neutral adult. Classical anthropometric
# rules of thumb; no dataset, so no licence.
_ANTHROPOMETRIC = {
    "shoulder_width": 0.245,
    "shoulder_depth": 0.105,
    "shoulder_slope": 0.030,
    "neck_width": 0.070,
    "neck_length": 0.052,
    "chest_width": 0.190,
    "chest_depth": 0.115,
    "waist_width": 0.160,
    "waist_depth": 0.105,
    "hip_width": 0.195,
    "hip_depth": 0.125,
    "upper_arm_length": 0.172,
    "upper_arm_radius": 0.035,
    "forearm_length": 0.157,
    "forearm_radius": 0.027,
    "thigh_length": 0.245,
    "thigh_width": 0.098,
    "thigh_depth": 0.098,
    "calf_length": 0.246,
    "calf_width": 0.068,
    "calf_depth": 0.070,
    "ankle_width": 0.038,
    "head_height": 0.130,
    "head_width": 0.092,
    "head_depth": 0.115,
}


@runtime_checkable
class ProportionsSource(Protocol):
    """Fills in the measurements a caller did not supply."""

    name: str

    def fractions(self, height_cm: float, weight_kg: float | None = None) -> dict[str, float]:
        """Return field name to fraction of standing height."""
        ...


@dataclass
class AnthropometricProportions:
    """The default. Fractions of height, independent of everything else."""

    name: str = "anthropometric"

    def fractions(self, height_cm: float, weight_kg: float | None = None) -> dict[str, float]:
        return dict(_ANTHROPOMETRIC)


@dataclass
class ScaledProportions:
    """Anthropometric fractions with a build adjustment.

    A heavier body is not a taller body's proportions scaled down: mass lands on
    the torso and barely touches limb length. This applies that skew without
    needing a dataset, as a stopgap between the flat table and a learned model.

    `build` runs roughly -1 (slight) to 1 (heavy).
    """

    build: float = 0.0
    name: str = "scaled"

    # How much each measurement responds to build. Lengths do not.
    _RESPONSE = {
        "waist_width": 0.34,
        "waist_depth": 0.40,
        "hip_width": 0.18,
        "hip_depth": 0.24,
        "chest_width": 0.14,
        "chest_depth": 0.20,
        "thigh_width": 0.20,
        "thigh_depth": 0.20,
        "upper_arm_radius": 0.16,
        "forearm_radius": 0.10,
        "calf_width": 0.12,
        "calf_depth": 0.12,
        "neck_width": 0.08,
    }

    def fractions(self, height_cm: float, weight_kg: float | None = None) -> dict[str, float]:
        build = self.build
        if weight_kg is not None and height_cm > 0:
            # BMI relative to a mid-normal 22, softly clamped either side.
            bmi = weight_kg / ((height_cm / 100.0) ** 2)
            build = max(-1.0, min(1.0, (bmi - 22.0) / 8.0))

        out = dict(_ANTHROPOMETRIC)
        for field, response in self._RESPONSE.items():
            out[field] = round(out[field] * (1.0 + build * response), 5)
        return out


class LearnedProportions:
    """Proportions from a mapping fitted to measured bodies.

    Carries no dataset. The model is a small coefficients file, so whichever
    bodies were used to fit it stay outside this repository with their licence.
    A model fitted on generated bodies is marked synthetic, and
    `describe()` reports that rather than letting it pass as measurement.
    """

    name = "learned"

    def __init__(self, model: object | None = None, model_path: str | None = None) -> None:
        from sveyra_human.body.learned import ProportionModel

        if model is None and model_path is None:
            raise ValueError(
                "LearnedProportions needs a fitted model. Fit one with "
                "sveyra_human.body.learned.fit_from_table, or pass model_path."
            )
        self._model = model if model is not None else ProportionModel.load(str(model_path))

    def describe(self) -> str:
        return (
            f"fitted on {self._model.sample_count} bodies "
            f"({self._model.provenance})"
        )

    def fractions(self, height_cm: float, weight_kg: float | None = None) -> dict[str, float]:
        if height_cm <= 0:
            raise ValueError("height_cm must be positive")
        # A body with no weight given still has to produce a body, so fall back
        # to a mid-normal BMI rather than refusing.
        weight = weight_kg if weight_kg is not None else 22.0 * (height_cm / 100.0) ** 2
        predicted = self._model.predict({"height_cm": height_cm, "weight_kg": weight})

        out = dict(_ANTHROPOMETRIC)
        for field, centimetres in predicted.items():
            if field in out and centimetres > 0:
                out[field] = centimetres / height_cm
        return out


DEFAULT_SOURCE: ProportionsSource = AnthropometricProportions()


def resolve(source: ProportionsSource | None) -> ProportionsSource:
    return source if source is not None else DEFAULT_SOURCE
