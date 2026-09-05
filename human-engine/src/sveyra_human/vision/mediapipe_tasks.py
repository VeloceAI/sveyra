"""MediaPipe Tasks adapters for segmentation and pose.

The older `mediapipe.solutions` API that `MediaPipeSegmenter` targets is gone
from the 0.10.3x wheels and from 1.0 entirely, so on a current install that
class cannot run at all. Tasks is the replacement, and it is a better fit here:
one dependency supplies both the person mask the silhouette fitter needs and
the landmarks the pose solver needs.

Tasks loads its weights from a file rather than bundling them, so a model path
has to be supplied. That is a feature for us: the model stays out of the
repository, and swapping a lighter one in is a path change.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from sveyra_human.pose.landmarks import Landmarks
from sveyra_human.vision.port import PersonSegmenter, SegmentationResult

# selfie_multiclass_256x256 labels. 0 is background; everything else is a person.
_BACKGROUND = 0


def _require(path: str | Path, what: str) -> Path:
    resolved = Path(path)
    if not resolved.is_file():
        raise FileNotFoundError(
            f"{what} model not found at {resolved}. Download it from "
            "https://storage.googleapis.com/mediapipe-models/ and pass its path."
        )
    return resolved


class MediaPipeTasksSegmenter(PersonSegmenter):
    """Person mask from MediaPipe's multiclass selfie segmenter."""

    name = "mediapipe-tasks-selfie"

    def __init__(self, model_path: str | Path) -> None:
        from mediapipe import Image, ImageFormat
        from mediapipe.tasks.python import BaseOptions, vision

        self._Image = Image
        self._ImageFormat = ImageFormat
        self._segmenter = vision.ImageSegmenter.create_from_options(
            vision.ImageSegmenterOptions(
                base_options=BaseOptions(
                    model_asset_path=str(_require(model_path, "segmentation"))
                ),
                running_mode=vision.RunningMode.IMAGE,
                output_category_mask=True,
            )
        )

    def segment(self, image: np.ndarray) -> SegmentationResult:
        rgb = np.ascontiguousarray(image[:, :, :3].astype(np.uint8))
        result = self._segmenter.segment(
            self._Image(image_format=self._ImageFormat.SRGB, data=rgb)
        )
        categories = result.category_mask.numpy_view()
        mask = (categories != _BACKGROUND).astype(np.float32)

        # The segmenter works at 256x256 and returns its own resolution; the
        # fitter measures in image pixels, so it has to come back the same size.
        if mask.shape != rgb.shape[:2]:
            mask = _resize_nearest(mask, rgb.shape[:2])
        return SegmentationResult(mask=mask, confidence=float(mask.mean() > 0.01))


class MediaPipeTasksPose(  # noqa: D101 - documented by the protocol
    object
):
    """The 33 BlazePose landmarks the pose solver is written against."""

    name = "mediapipe-tasks-pose"

    def __init__(self, model_path: str | Path) -> None:
        from mediapipe import Image, ImageFormat
        from mediapipe.tasks.python import BaseOptions, vision

        self._Image = Image
        self._ImageFormat = ImageFormat
        self._landmarker = vision.PoseLandmarker.create_from_options(
            vision.PoseLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=str(_require(model_path, "pose"))),
                running_mode=vision.RunningMode.IMAGE,
                num_poses=1,
            )
        )

    def detect(self, image: np.ndarray) -> Landmarks | None:
        rgb = np.ascontiguousarray(image[:, :, :3].astype(np.uint8))
        result = self._landmarker.detect(
            self._Image(image_format=self._ImageFormat.SRGB, data=rgb)
        )
        if not result.pose_world_landmarks:
            return None

        world = result.pose_world_landmarks[0]
        points = np.array([[p.x, -p.y, p.z] for p in world], dtype=float)
        visibility = np.array([getattr(p, "visibility", 1.0) for p in world], dtype=float)
        if points.shape[0] != 33:
            return None

        on_image = result.pose_landmarks[0] if result.pose_landmarks else world
        image_points = np.array([[p.x, p.y] for p in on_image], dtype=float)
        return Landmarks(
            points=points, visibility=visibility, image_points=image_points
        )


def _resize_nearest(mask: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    rows = (np.linspace(0, mask.shape[0] - 1, shape[0])).round().astype(int)
    cols = (np.linspace(0, mask.shape[1] - 1, shape[1])).round().astype(int)
    return mask[rows][:, cols]
