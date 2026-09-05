"""Torso widths read from a silhouette, guided by pose landmarks.

The band-profile fitter takes the widest row in each horizontal band. On a
photograph of someone standing normally that row runs shoulder to shoulder
through both arms, so a chest measurement is really an arm span, and every
body comes back about the same width regardless of who is in the picture.

Landmarks fix that. Knowing where the shoulders and hips are means the scan can
start at the body's own midline and stop at the first gap, which is the edge of
the torso when the arms are clear of it. Where an arm touches the body there is
no gap to find, and the extraction says so rather than returning the arm.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Fractions of the shoulder-to-hip distance, measured down from the shoulders.
LEVELS = {"chest": 0.18, "waist": 0.62, "hip": 1.0}

# How much wider than the joint-to-joint span the silhouette may reasonably be
# before it must be carrying an arm. Soft tissue puts a real torso up to about a
# third wider than the landmarks; an arm adds far more than that.
MAX_FLESH = 1.35


@dataclass
class TorsoWidths:
    """Widths in pixels at each level, and whether each one is trustworthy."""

    widths: dict[str, float]
    clean: dict[str, bool]
    shoulder_px: float
    scale_cm_per_px: float

    def centimetres(self) -> dict[str, float]:
        return {k: v * self.scale_cm_per_px for k, v in self.widths.items()}

    @property
    def usable(self) -> bool:
        return all(self.clean.values())


def _run_from_midline(row: np.ndarray, centre: int) -> tuple[float, bool]:
    """Width of the unbroken run of subject containing `centre`.

    Returns the width and whether both edges were real gaps rather than the
    frame border, which is what tells the caller the arms were clear.
    """
    width = row.shape[0]
    centre = int(np.clip(centre, 0, width - 1))
    if not row[centre]:
        near = np.flatnonzero(row)
        if not near.size:
            return 0.0, False
        centre = int(near[np.argmin(np.abs(near - centre))])

    left = centre
    while left > 0 and row[left - 1]:
        left -= 1
    right = centre
    while right < width - 1 and row[right + 1]:
        right += 1

    clean = left > 0 and right < width - 1
    return float(right - left + 1), clean


def extract(
    mask: np.ndarray,
    landmarks: np.ndarray,
    visibility: np.ndarray,
    height_cm: float,
) -> TorsoWidths | None:
    """Torso widths at chest, waist and hip, in pixels and centimetres.

    `landmarks` are image-space (x, y) in pixels for the 33 BlazePose points.
    Returns None when the shoulders or hips were not seen, because without them
    there is no midline and no vertical scale for the torso.
    """
    needed = (11, 12, 23, 24)  # shoulders and hips
    if any(visibility[i] < 0.6 for i in needed):
        return None

    shoulder_l, shoulder_r = landmarks[11], landmarks[12]
    hip_l, hip_r = landmarks[23], landmarks[24]
    shoulder_y = (shoulder_l[1] + shoulder_r[1]) / 2.0
    hip_y = (hip_l[1] + hip_r[1]) / 2.0
    span = hip_y - shoulder_y
    if span <= 1:
        return None

    midline = (shoulder_l[0] + shoulder_r[0] + hip_l[0] + hip_r[0]) / 4.0
    solid = mask > 0.5

    # What the landmarks alone say the body is, joint centre to joint centre.
    # Flesh puts the silhouette wider than this, but not unboundedly: a run that
    # far exceeds it has swallowed an arm, and there was no gap to stop at
    # because the arm was touching. That is the case the frame-border test
    # cannot see, and the one that made every body come back the same width.
    landmark_span = {
        "chest": abs(shoulder_l[0] - shoulder_r[0]),
        "waist": (abs(shoulder_l[0] - shoulder_r[0]) + abs(hip_l[0] - hip_r[0])) / 2.0,
        "hip": abs(hip_l[0] - hip_r[0]),
    }

    widths: dict[str, float] = {}
    clean: dict[str, bool] = {}
    for name, fraction in LEVELS.items():
        y = int(round(shoulder_y + span * fraction))
        y = int(np.clip(y, 0, solid.shape[0] - 1))
        width, bounded = _run_from_midline(solid[y], int(round(midline)))
        widths[name] = width
        clean[name] = bounded and width <= landmark_span[name] * MAX_FLESH

    rows = np.flatnonzero(solid.any(axis=1))
    if rows.size < 2:
        return None
    scale = height_cm / float(rows[-1] - rows[0] + 1)

    return TorsoWidths(
        widths=widths,
        clean=clean,
        shoulder_px=float(abs(shoulder_l[0] - shoulder_r[0])),
        scale_cm_per_px=scale,
    )
