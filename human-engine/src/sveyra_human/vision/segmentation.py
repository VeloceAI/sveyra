"""Separating a person from the background.

`BackgroundContrastSegmenter` needs no model and no GPU. It estimates the
background from the image border, keeps pixels that differ from it, and takes
the largest connected region. That is enough for the kind of photograph this
product asks for - one person, standing, against a reasonably plain wall - and
it costs milliseconds.

It is not a general-purpose segmenter and does not pretend to be. Where it is
unsure it says so through `SegmentationResult.confidence`, and a MediaPipe
adapter is available for harder images.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import ndimage

from sveyra_human.vision.port import PersonSegmenter, SegmentationResult

# A person photographed full length occupies roughly this share of the frame.
# Well outside it means the mask probably caught the wall or only a limb.
PLAUSIBLE_COVERAGE = (0.04, 0.60)


def _as_float_rgb(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        image = np.stack([image] * 3, axis=-1)
    if image.ndim != 3 or image.shape[2] < 3:
        raise ValueError("image must be HxW, HxWx3 or HxWx4")
    rgb = image[:, :, :3].astype(np.float64)
    return rgb / 255.0 if rgb.max() > 1.5 else rgb


@dataclass
class BackgroundContrastSegmenter(PersonSegmenter):
    """Border-sampled background subtraction with a largest-region pick."""

    border_fraction: float = 0.06
    threshold_scale: float = 2.5
    min_threshold: float = 0.10

    def segment(self, image: np.ndarray) -> SegmentationResult:
        rgb = _as_float_rgb(image)
        height, width = rgb.shape[:2]
        border = max(1, int(min(height, width) * self.border_fraction))

        # The frame edge is background far more often than it is subject.
        edge = np.concatenate(
            [
                rgb[:border].reshape(-1, 3),
                rgb[-border:].reshape(-1, 3),
                rgb[:, :border].reshape(-1, 3),
                rgb[:, -border:].reshape(-1, 3),
            ]
        )
        background = np.median(edge, axis=0)
        spread = float(np.median(np.abs(edge - background))) or 0.01

        distance = np.linalg.norm(rgb - background, axis=2)
        threshold = max(self.min_threshold, spread * self.threshold_scale)
        mask = distance > threshold

        # Order matters. Opening first removes the background speckle a noisy or
        # unevenly lit wall produces; filling holes before that lets speckle form
        # a connected ring around the frame whose "interior" is the whole image,
        # which swallows everything.
        mask = ndimage.binary_opening(mask, structure=np.ones((3, 3)))
        mask = ndimage.binary_closing(mask, structure=np.ones((5, 5)))

        labels, count = ndimage.label(mask)
        if count == 0:
            return SegmentationResult(mask=np.zeros((height, width), dtype=bool), confidence=0.0)
        sizes = ndimage.sum_labels(mask, labels, index=range(1, count + 1))
        largest = int(np.argmax(sizes)) + 1
        # Fill only inside the chosen subject, never across the frame.
        person = ndimage.binary_fill_holes(labels == largest)

        return SegmentationResult(
            mask=person,
            confidence=self._confidence(person, distance, threshold),
        )

    def _confidence(self, mask: np.ndarray, distance: np.ndarray, threshold: float) -> float:
        """How much this mask deserves to be believed.

        Two independent signals: whether the region is a plausible size for a
        standing person, and how cleanly it separates from the background. A
        subject the same colour as the wall scores low on the second even when
        the first looks fine.
        """
        coverage = float(mask.mean())
        if coverage <= 0.0:
            return 0.0
        lo, hi = PLAUSIBLE_COVERAGE
        if coverage < lo:
            size_score = coverage / lo
        elif coverage > hi:
            size_score = max(0.0, 1.0 - (coverage - hi) / hi)
        else:
            size_score = 1.0

        inside = distance[mask]
        separation = float(np.clip((inside.mean() - threshold) / max(threshold, 1e-6), 0.0, 1.0))
        return round(float(np.clip(0.35 * size_score + 0.65 * separation, 0.0, 1.0)), 4)


class MediaPipeSegmenter(PersonSegmenter):
    """Adapter for MediaPipe selfie segmentation.

    Optional. Install with the `vision` extra. Imported lazily so the engine
    never pays for it, and so a missing install fails with an instruction rather
    than an ImportError at module load.
    """

    def __init__(self, model_selection: int = 1) -> None:
        self._model_selection = model_selection
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
            self._solution = mp.solutions.selfie_segmentation.SelfieSegmentation(
                model_selection=self._model_selection
            )
        return self._solution

    def segment(self, image: np.ndarray) -> SegmentationResult:  # pragma: no cover - optional dep
        solution = self._ensure()
        rgb = (_as_float_rgb(image) * 255).astype(np.uint8)
        result = solution.process(rgb)
        confidence_map = np.asarray(result.segmentation_mask)
        mask = confidence_map > 0.5
        return SegmentationResult(
            mask=mask,
            confidence=float(confidence_map[mask].mean()) if mask.any() else 0.0,
        )
