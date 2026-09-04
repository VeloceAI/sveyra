"""Finding hair in a photograph.

Hair is separated from skin by sampling the person's actual skin colour and
keeping what differs from it, rather than by testing against a fixed idea of
what skin looks like. A fixed rule fails immediately: dark brown hair has the
same reddish channel ratios as skin and only differs in brightness, while blonde
hair differs in brightness but not much in hue.

The lower part of the head region is reliably face. That is the reference, and
everything measured against it is per-person, so it survives skin tone, lighting
and hair colour together.

Deliberately conservative: where it cannot tell, it returns nothing rather than
claiming hair that may be shadow. An empty hair mask produces a bald avatar,
which is visibly wrong and therefore honest. A wrong one is worse.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import ndimage

# Hair sits above and around the face. Fraction of the person mask's height,
# measured down from the crown.
HEAD_REGION = 0.22

# The lower part of the head region used as the skin reference. Sampling the
# whole head would average the hair back in.
SKIN_SAMPLE_BAND = (0.55, 1.0)

# Colour distance from the sampled skin, in normalised RGB, beyond which a
# pixel is not skin.
SKIN_DISTANCE = 0.16


@dataclass(frozen=True)
class HairMask:
    mask: np.ndarray
    confidence: float

    def coverage(self) -> float:
        return float(self.mask.mean()) if self.mask.size else 0.0


def _normalised_rgb(image: np.ndarray) -> np.ndarray:
    rgb = image[:, :, :3].astype(np.float64)
    return rgb / 255.0 if rgb.max() > 1.5 else rgb


def segment_hair(image: np.ndarray, person_mask: np.ndarray) -> HairMask:
    """Hair within the head region of a person mask."""
    if image.shape[:2] != person_mask.shape:
        raise ValueError("image and person mask must have the same resolution")
    if not person_mask.any():
        return HairMask(mask=np.zeros_like(person_mask), confidence=0.0)

    rows = np.nonzero(person_mask.any(axis=1))[0]
    top, bottom = int(rows.min()), int(rows.max())
    head_bottom = top + int((bottom - top) * HEAD_REGION)

    region = np.zeros_like(person_mask)
    region[top : head_bottom + 1] = person_mask[top : head_bottom + 1]
    if not region.any():
        return HairMask(mask=np.zeros_like(person_mask), confidence=0.0)

    rgb = _normalised_rgb(image)
    skin = _sample_skin(rgb, region, top, head_bottom)
    if skin is None:
        return HairMask(mask=np.zeros_like(person_mask), confidence=0.0)

    distance = np.linalg.norm(rgb - skin, axis=2)
    hair = region & (distance > SKIN_DISTANCE)

    hair = ndimage.binary_opening(hair, structure=np.ones((3, 3)))
    labels, count = ndimage.label(hair)
    if count == 0:
        return HairMask(mask=np.zeros_like(person_mask), confidence=0.0)
    sizes = ndimage.sum_labels(hair, labels, index=range(1, count + 1))
    hair = labels == int(np.argmax(sizes)) + 1

    return HairMask(mask=hair, confidence=_confidence(hair, region, distance))


def _sample_skin(
    rgb: np.ndarray, region: np.ndarray, top: int, head_bottom: int
) -> np.ndarray | None:
    """Median colour of the lower head region, which is face rather than hair."""
    span = head_bottom - top
    if span <= 0:
        return None
    lo = top + int(span * SKIN_SAMPLE_BAND[0])
    hi = head_bottom + 1
    band = np.zeros_like(region)
    band[lo:hi] = region[lo:hi]
    if not band.any():
        return None
    return np.median(rgb[band], axis=0)


def _confidence(hair: np.ndarray, region: np.ndarray, distance: np.ndarray) -> float:
    """Two signals: a plausible share of the head, and clean separation.

    Almost no hair suggests a bald subject or a failed split; almost all of it
    suggests the face was swallowed. Both deserve low confidence.
    """
    region_size = float(region.sum())
    if region_size <= 0 or not hair.any():
        return 0.0
    share = float(hair.sum()) / region_size
    if share < 0.03 or share > 0.97:
        return 0.0
    size_score = float(np.clip(1.0 - abs(share - 0.45) * 1.4, 0.0, 1.0))
    separation = float(
        np.clip((distance[hair].mean() - SKIN_DISTANCE) / SKIN_DISTANCE, 0.0, 1.0)
    )
    return round(float(np.clip(0.4 * size_score + 0.6 * separation, 0.0, 1.0)), 4)
