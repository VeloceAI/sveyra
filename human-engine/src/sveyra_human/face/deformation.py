"""Shaping the head from face parameters.

The head cage is a ring stack like every other part, so shaping a face means
scaling rings by height rather than moving individual vertices. Coarse by
design: a jaw is a width at a height, not a sculpt.

Depth is left alone. A single front view constrains nothing about projection,
so inventing a nose profile here would be fabrication rather than
reconstruction.
"""

from __future__ import annotations

import numpy as np

from sveyra_human.body.cage import CagePart
from sveyra_human.face.parameters import FaceParameters

# Height fraction of the face (0 = chin, 1 = hairline) -> which width governs it.
_PROFILE: tuple[tuple[float, str], ...] = (
    (0.00, "chin_width"),
    (0.22, "jaw_width"),
    (0.55, "cheekbone_width"),
    (0.80, "forehead_width"),
    (1.00, "forehead_width"),
)


def width_profile(params: FaceParameters, samples: int = 16) -> np.ndarray:
    """Face width in centimetres at evenly spaced heights, chin to hairline."""
    heights = np.array([h for h, _ in _PROFILE])
    widths = np.array([float(getattr(params, name)) for _, name in _PROFILE])
    return np.interp(np.linspace(0.0, 1.0, samples), heights, widths)


def apply_face_shape(
    head: CagePart, params: FaceParameters, head_bottom_cm: float, head_top_cm: float
) -> CagePart:
    """Return a new head cage scaled to the face.

    Rings below the chin and above the hairline are left untouched: they are
    neck and cranium, which no face parameter describes.
    """
    if head_top_cm <= head_bottom_cm:
        raise ValueError("head_top_cm must sit above head_bottom_cm")

    rings = head.rings.copy()
    chin = head_bottom_cm
    hairline = chin + float(params.face_length)
    if hairline > head_top_cm:
        hairline = head_top_cm

    for level in range(rings.shape[0]):
        y = float(rings[level, :, 1].mean())
        if y < chin or y > hairline:
            continue
        fraction = (y - chin) / max(hairline - chin, 1e-6)
        target = float(np.interp(fraction, [h for h, _ in _PROFILE],
                                 [float(getattr(params, n)) for _, n in _PROFILE]))
        current = float(rings[level, :, 0].max() - rings[level, :, 0].min())
        if current < 1e-6:
            continue
        centre_x = float(rings[level, :, 0].mean())
        rings[level, :, 0] = centre_x + (rings[level, :, 0] - centre_x) * (target / current)

    return CagePart(
        name=head.name,
        rings=rings,
        closed_bottom=head.closed_bottom,
        closed_top=head.closed_top,
    )
