"""Vision contracts.

Everything the engine needs from an image is declared here. MediaPipe is one
implementation of these, not the definition of them, so it can be swapped for a
different segmenter or landmarker without the body engine noticing.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class Landmark:
    """A detected point, in normalised image coordinates (0-1)."""

    name: str
    x: float
    y: float
    visibility: float = 1.0


@dataclass(frozen=True)
class PoseLandmarks:
    points: dict[str, Landmark] = field(default_factory=dict)

    def get(self, name: str) -> Landmark | None:
        return self.points.get(name)

    @property
    def confidence(self) -> float:
        if not self.points:
            return 0.0
        return float(np.mean([p.visibility for p in self.points.values()]))


@dataclass(frozen=True)
class SegmentationResult:
    """A person mask plus how much of it should be believed."""

    mask: np.ndarray
    confidence: float = 1.0

    def coverage(self) -> float:
        return float(self.mask.mean()) if self.mask.size else 0.0


class PoseEstimator:
    def estimate(self, image: np.ndarray) -> PoseLandmarks:
        raise NotImplementedError


class PersonSegmenter:
    def segment(self, image: np.ndarray) -> SegmentationResult:
        raise NotImplementedError


class FaceLandmarker:
    def landmarks(self, image: np.ndarray) -> PoseLandmarks:
        raise NotImplementedError
