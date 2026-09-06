"""Pose landmarks.

Only the MediaPipe adapter exists; there is no model-free fallback, because
guessing joint positions from a silhouette would be a worse lie than admitting
the landmarks are unavailable. The fitter does not require pose today - it works
from silhouettes alone - so this is additive rather than blocking.
"""

from __future__ import annotations

import numpy as np

from sveyra_human.vision.port import Landmark, PoseEstimator, PoseLandmarks

# MediaPipe index -> our joint vocabulary. Only the joints the body model uses.
MEDIAPIPE_JOINTS = {
    11: "shoulder_L", 12: "shoulder_R",
    13: "elbow_L", 14: "elbow_R",
    15: "wrist_L", 16: "wrist_R",
    23: "hip_L", 24: "hip_R",
    25: "knee_L", 26: "knee_R",
    27: "ankle_L", 28: "ankle_R",
}


class MediaPipePose(PoseEstimator):
    """Adapter for MediaPipe Pose. Optional; install the `vision` extra."""

    def __init__(self, model_complexity: int = 1) -> None:
        self._complexity = model_complexity
        self._solution = None

    def _ensure(self):
        if self._solution is None:
            try:
                import mediapipe as mp
            except ImportError as exc:  # pragma: no cover - depends on the install
                raise RuntimeError(
                    "MediaPipe is not installed. Install the vision extra: "
                    'pip install -e ".[vision]"'
                ) from exc
            self._solution = mp.solutions.pose.Pose(
                static_image_mode=True, model_complexity=self._complexity
            )
        return self._solution

    def estimate(self, image: np.ndarray) -> PoseLandmarks:  # pragma: no cover - optional dep
        result = self._ensure().process(image)
        if not result.pose_landmarks:
            return PoseLandmarks()
        points: dict[str, Landmark] = {}
        for index, name in MEDIAPIPE_JOINTS.items():
            lm = result.pose_landmarks.landmark[index]
            points[name] = Landmark(name=name, x=float(lm.x), y=float(lm.y),
                                    visibility=float(lm.visibility))
        return PoseLandmarks(points=points)
