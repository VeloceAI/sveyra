"""Lightweight vision.

Interfaces first, implementations second: MediaPipe is one way to satisfy these
contracts, never the definition of them.
"""

from sveyra_human.vision.port import (
    FaceLandmarker,
    Landmark,
    PersonSegmenter,
    PoseEstimator,
    PoseLandmarks,
    SegmentationResult,
)
from sveyra_human.vision.segmentation import (
    BackgroundContrastSegmenter,
    MediaPipeSegmenter,
)
from sveyra_human.vision.silhouette import (
    clean_mask,
    crop_to_subject,
    is_full_body,
    silhouette_from_segmentation,
    vertical_extent,
)

__all__ = [
    "BackgroundContrastSegmenter",
    "FaceLandmarker",
    "Landmark",
    "MediaPipeSegmenter",
    "PersonSegmenter",
    "PoseEstimator",
    "PoseLandmarks",
    "SegmentationResult",
    "clean_mask",
    "crop_to_subject",
    "is_full_body",
    "silhouette_from_segmentation",
    "vertical_extent",
]
