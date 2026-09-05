"""The landmark vocabulary a pose detector speaks.

BlazePose GHUM's 33 points are the de-facto standard: MediaPipe emits them,
MakeHuman.js consumes them, and every other detector worth swapping in either
produces them or maps onto them cheaply. Naming them here rather than importing
a detector keeps the solver testable with no model present.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

NAMES: tuple[str, ...] = (
    "nose",
    "left_eye_inner", "left_eye", "left_eye_outer",
    "right_eye_inner", "right_eye", "right_eye_outer",
    "left_ear", "right_ear",
    "mouth_left", "mouth_right",
    "left_shoulder", "right_shoulder",
    "left_elbow", "right_elbow",
    "left_wrist", "right_wrist",
    "left_pinky", "right_pinky",
    "left_index", "right_index",
    "left_thumb", "right_thumb",
    "left_hip", "right_hip",
    "left_knee", "right_knee",
    "left_ankle", "right_ankle",
    "left_heel", "right_heel",
    "left_foot_index", "right_foot_index",
)

INDEX: dict[str, int] = {name: i for i, name in enumerate(NAMES)}

# Below this a landmark is a guess, and a guess moves a limb somewhere the
# person never put it. The joint is left at rest instead, and reported as unsolved.
MIN_VISIBILITY = 0.6


@dataclass(frozen=True)
class Landmarks:
    """33 points in 3D plus a per-point visibility, as a detector returns them.

    Coordinates are metres in the detector's own frame with Y up; only
    directions between points matter to the solver, so the origin is free.
    """

    points: np.ndarray
    visibility: np.ndarray
    # Normalised (x, y) in the frame the photograph was taken in. The solver
    # works in world space, but anything measuring the image itself — a
    # silhouette width, a crop — needs where the joint landed on the picture.
    image_points: np.ndarray | None = None

    def __post_init__(self) -> None:
        if self.points.shape != (33, 3):
            raise ValueError(f"expected 33 points of xyz, got {self.points.shape}")
        if self.visibility.shape != (33,):
            raise ValueError(f"expected 33 visibilities, got {self.visibility.shape}")

    def get(self, name: str) -> np.ndarray:
        return self.points[INDEX[name]]

    def seen(self, *names: str) -> bool:
        return all(self.visibility[INDEX[n]] >= MIN_VISIBILITY for n in names)

    def midpoint(self, a: str, b: str) -> np.ndarray:
        return (self.get(a) + self.get(b)) / 2.0

    @classmethod
    def from_rows(cls, rows: list[tuple[float, float, float, float]]) -> Landmarks:
        """Build from a detector's (x, y, z, visibility) rows."""
        if len(rows) != 33:
            raise ValueError(f"expected 33 landmark rows, got {len(rows)}")
        data = np.asarray(rows, dtype=float)
        return cls(points=data[:, :3].copy(), visibility=data[:, 3].copy())
