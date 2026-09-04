"""Changing a body without rebuilding the person.

An avatar is a parameter set, so "show me twelve kilos lighter" is arithmetic on
that set rather than a new reconstruction. The photographs are not needed again,
and because topology is fixed, the result is morph-compatible with the original:
the same vertices in the same order, so a garment fitted to one fits the other.

The transforms are deliberately anatomical rather than uniform scaling. Losing
weight is not shrinking: it takes from the waist and abdomen first, barely
touches the ribcage, and leaves bone width alone entirely.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from sveyra_human.body.parameters import BodyParameters

# How much of a weight change each measurement absorbs. Soft tissue moves,
# skeletal width does not: shoulder and ankle stay put while the waist carries
# most of it.
_WEIGHT_RESPONSE: dict[str, float] = {
    "waist_width": 1.00,
    "waist_depth": 1.15,
    "hip_width": 0.55,
    "hip_depth": 0.70,
    "chest_width": 0.40,
    "chest_depth": 0.55,
    "thigh_width": 0.60,
    "thigh_depth": 0.60,
    "upper_arm_radius": 0.45,
    "forearm_radius": 0.30,
    "calf_width": 0.35,
    "calf_depth": 0.35,
    "neck_width": 0.25,
}

# Muscle broadens the shoulders and limbs and narrows nothing.
_MUSCLE_RESPONSE: dict[str, float] = {
    "shoulder_width": 0.55,
    "chest_width": 0.70,
    "chest_depth": 0.80,
    "upper_arm_radius": 1.00,
    "forearm_radius": 0.75,
    "thigh_width": 0.80,
    "thigh_depth": 0.80,
    "calf_width": 0.70,
    "calf_depth": 0.70,
    "neck_width": 0.45,
    "waist_width": 0.10,
}

# Centimetres of waist *width* per kilogram. Calibrated so that the resulting
# girth change matches the commonly cited figure of roughly 1 cm of waist
# circumference per kilogram: width feeds a superellipse perimeter, which
# amplifies it about threefold, so the per-kg width figure has to be well under
# the per-kg girth figure. An earlier 0.65 moved girth about twice as far as any
# real body does.
CM_PER_KG_AT_WAIST = 0.30

# Nothing may shrink below this fraction of its starting value: at some point a
# waist is bone and cartilage and stops responding.
FLOOR_SCALE = 0.60
CEILING_SCALE = 2.0


@dataclass(frozen=True)
class TransformReport:
    """What a transform actually did, and how much to trust it."""

    kind: str
    magnitude: float
    changed: dict[str, tuple[float, float]]
    warnings: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "magnitude": round(self.magnitude, 3),
            "changed": {
                name: [round(before, 3), round(after, 3)]
                for name, (before, after) in self.changed.items()
            },
            "warnings": list(self.warnings),
        }


def _apply(
    params: BodyParameters,
    response: dict[str, float],
    delta_cm: float,
    kind: str,
    magnitude: float,
    warnings: list[str],
) -> tuple[BodyParameters, TransformReport]:
    changed: dict[str, tuple[float, float]] = {}
    updated = BodyParameters.from_dict(params.to_dict())

    for name, share in response.items():
        before = float(getattr(updated, name))
        raw = before + delta_cm * share
        lower, upper = before * FLOOR_SCALE, before * CEILING_SCALE
        after = float(np.clip(raw, lower, upper))
        if abs(after - before) > 1e-9:
            setattr(updated, name, round(after, 4))
            changed[name] = (before, after)

    if not changed:
        warnings.append("The requested change was too small to alter any measurement.")
    return updated, TransformReport(
        kind=kind, magnitude=magnitude, changed=changed, warnings=warnings
    )


def change_weight(
    params: BodyParameters, kilograms: float
) -> tuple[BodyParameters, TransformReport]:
    """Gain or lose weight. Negative loses.

    Soft tissue absorbs it in anatomical proportion; height and skeletal widths
    are untouched, because losing weight does not narrow a shoulder.
    """
    warnings = [
        "Weight change is applied by an anthropometric rule of thumb, not a "
        "model fitted to this person. Treat the result as indicative."
    ]
    if abs(kilograms) > 30.0:
        warnings.append(
            "Beyond about 30 kg the linear response stops holding and the "
            "result is a rough sketch."
        )
    delta_cm = kilograms * CM_PER_KG_AT_WAIST
    return _apply(params, _WEIGHT_RESPONSE, delta_cm, "weight", kilograms, warnings)


def change_muscle(
    params: BodyParameters, level: float
) -> tuple[BodyParameters, TransformReport]:
    """Add or remove muscle. `level` runs roughly -1 to 1."""
    warnings = [
        "Muscle change broadens shoulders and limbs by an anthropometric rule "
        "of thumb, not a fitted model."
    ]
    if abs(level) > 1.0:
        warnings.append("Levels beyond 1 are extrapolation and will look exaggerated.")
    delta_cm = level * 4.0
    return _apply(params, _MUSCLE_RESPONSE, delta_cm, "muscle", level, warnings)


def scale_measurement(
    params: BodyParameters, field: str, factor: float
) -> tuple[BodyParameters, TransformReport]:
    """Scale one named measurement directly, for manual adjustment.

    No anatomical response here: the caller asked for exactly this change to
    exactly this measurement.
    """
    if not hasattr(params, field) or getattr(params, field) is None:
        raise ValueError(f"unknown or unset measurement: {field}")
    if factor <= 0:
        raise ValueError("factor must be positive")

    updated = BodyParameters.from_dict(params.to_dict())
    before = float(getattr(updated, field))
    after = round(before * factor, 4)
    setattr(updated, field, after)

    warnings: list[str] = []
    if factor < FLOOR_SCALE or factor > CEILING_SCALE:
        warnings.append(
            f"A factor of {factor} is outside the range a human measurement "
            "normally varies over; the result may not look anatomical."
        )
    return updated, TransformReport(
        kind="scale", magnitude=factor, changed={field: (before, after)}, warnings=warnings
    )


def interpolate(
    start: BodyParameters, end: BodyParameters, t: float
) -> BodyParameters:
    """Blend between two bodies. `t` of 0 is start, 1 is end.

    Useful for animating a change over time, and for previewing a goal partway.
    Heights must match: interpolating stature would be a different person.
    """
    if not 0.0 <= t <= 1.0:
        raise ValueError("t must be between 0 and 1")
    if abs(float(start.height) - float(end.height)) > 1e-6:
        raise ValueError("cannot interpolate between bodies of different heights")

    blended = BodyParameters.from_dict(start.to_dict())
    for name, value in start.to_dict().items():
        if name in ("height", "extra") or not isinstance(value, (int, float)):
            continue
        other = getattr(end, name, None)
        if other is None:
            continue
        setattr(blended, name, round(float(value) * (1.0 - t) + float(other) * t, 4))
    return blended
