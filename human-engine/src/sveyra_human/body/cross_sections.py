"""Horizontal slices through the body.

A cross section is a width and a depth at some height, plus a shape exponent.
Front photographs constrain width, side photographs constrain depth; V1 gets
both from BodyParameters instead, and Phase 3 will drive them from silhouettes.

The exponent is a superellipse power: 2.0 is an ellipse, higher is squarer. It
exists so a ribcage and a waist need not be forced into the same shape family.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from sveyra_human.body.parameters import BodyParameters


@dataclass(frozen=True)
class CrossSection:
    y: float
    width: float
    depth: float
    exponent: float = 2.0

    def outline(self, samples: int) -> np.ndarray:
        """Return `samples` points around this slice, counter-clockwise, XZ plane."""
        t = np.linspace(0.0, 2.0 * np.pi, samples, endpoint=False)
        n = 2.0 / self.exponent
        cos_t, sin_t = np.cos(t), np.sin(t)
        # Superellipse in the signed-power form; reduces to an ellipse at n == 1.
        x = np.sign(cos_t) * np.abs(cos_t) ** n * (self.width / 2.0)
        z = np.sign(sin_t) * np.abs(sin_t) ** n * (self.depth / 2.0)
        y = np.full(samples, self.y)
        return np.stack([x, y, z], axis=1)


def torso_profile(params: BodyParameters) -> list[CrossSection]:
    """Key slices from hip to neck, in ascending height.

    Only landmark levels are listed here. Intermediate slices come from
    `resample`, so the profile stays small and interpretable.
    """
    return [
        CrossSection(params.level_cm("hip"), float(params.hip_width), float(params.hip_depth), 2.4),
        CrossSection(
            params.level_cm("waist"), float(params.waist_width), float(params.waist_depth), 2.2
        ),
        CrossSection(
            params.level_cm("chest"), float(params.chest_width), float(params.chest_depth), 2.6
        ),
        CrossSection(
            params.level_cm("shoulder"),
            float(params.shoulder_width) * 0.82,
            float(params.shoulder_depth),
            2.4,
        ),
        CrossSection(
            params.level_cm("neck"), float(params.neck_width), float(params.neck_width), 2.0
        ),
    ]


def resample(profile: list[CrossSection], levels: int) -> list[CrossSection]:
    """Interpolate a key-slice profile onto `levels` evenly spaced heights.

    Linear in width, depth and exponent. Smoother schemes are a later swap;
    linear is deterministic and cheap, which is what V1 needs.
    """
    if levels < 2:
        raise ValueError("levels must be at least 2")
    if len(profile) < 2:
        raise ValueError("profile needs at least two cross sections")

    ordered = sorted(profile, key=lambda c: c.y)
    ys = np.array([c.y for c in ordered])
    widths = np.array([c.width for c in ordered])
    depths = np.array([c.depth for c in ordered])
    exps = np.array([c.exponent for c in ordered])

    targets = np.linspace(ys[0], ys[-1], levels)
    return [
        CrossSection(
            float(y),
            float(np.interp(y, ys, widths)),
            float(np.interp(y, ys, depths)),
            float(np.interp(y, ys, exps)),
        )
        for y in targets
    ]
