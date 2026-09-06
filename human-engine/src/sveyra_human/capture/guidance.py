"""Telling someone how to take a photograph the engine can actually use.

Validation says a view is unusable. That is not enough: a person holding a
phone needs to know *what to change*. Every check here returns an instruction
in the imperative, naming the fix rather than the defect, because "step back
until your feet are in frame" is actionable and "subject does not span enough
of the frame" is not.

Ordered by what to fix first. Someone told five things at once fixes none.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np

from sveyra_human.vision.silhouette import vertical_extent


class Severity(str, Enum):
    BLOCKING = "blocking"  # the photograph cannot be used at all
    ADVISORY = "advisory"  # usable, but the fit will be worse


@dataclass(frozen=True)
class Instruction:
    severity: Severity
    message: str
    code: str

    @property
    def blocking(self) -> bool:
        return self.severity is Severity.BLOCKING


@dataclass
class CaptureGuidance:
    view: str
    usable: bool
    framing_score: float
    instructions: list[Instruction]

    def to_dict(self) -> dict[str, object]:
        return {
            "view": self.view,
            "usable": self.usable,
            "framing_score": round(self.framing_score, 3),
            "instructions": [
                {"severity": i.severity.value, "message": i.message, "code": i.code}
                for i in self.instructions
            ],
        }

    @property
    def headline(self) -> str:
        """The one thing to say. Nothing to fix is worth saying too."""
        if not self.instructions:
            return "Looks good."
        return self.instructions[0].message


# A standing person should fill most of the frame's height without touching it.
IDEAL_HEIGHT_SHARE = (0.72, 0.94)
MIN_HEIGHT_SHARE = 0.55
# Off-centre by more than this fraction of frame width and the fit skews.
CENTRE_TOLERANCE = 0.12
DARK_THRESHOLD = 0.18
BRIGHT_THRESHOLD = 0.93


def guide_capture(
    view: str, image: np.ndarray, mask: np.ndarray, confidence: float
) -> CaptureGuidance:
    """Turn one photograph into instructions the person can act on."""
    instructions: list[Instruction] = []

    if not mask.any():
        instructions.append(
            Instruction(
                Severity.BLOCKING,
                "Stand where the camera can see you, against a plain wall.",
                "no_subject",
            )
        )
        return CaptureGuidance(view, False, 0.0, instructions)

    height_px, width_px = mask.shape
    top, bottom = vertical_extent(mask)
    share = (bottom - top + 1) / height_px
    columns = np.nonzero(mask.any(axis=0))[0]
    centre = (float(columns.min()) + float(columns.max())) / 2.0
    offset = (centre - width_px / 2.0) / width_px

    # Framing first: nothing else matters if the body is cut off.
    if share < MIN_HEIGHT_SHARE:
        instructions.append(
            Instruction(
                Severity.BLOCKING,
                "Move the phone further away until your head and feet are both in frame.",
                "too_far_or_cropped",
            )
        )
    elif top <= 1 or bottom >= height_px - 2:
        instructions.append(
            Instruction(
                Severity.BLOCKING,
                "Step back a little. Your head or feet are touching the edge of the frame.",
                "touching_edge",
            )
        )
    elif share > IDEAL_HEIGHT_SHARE[1]:
        instructions.append(
            Instruction(
                Severity.ADVISORY,
                "Step back slightly to leave a little room above your head.",
                "too_close",
            )
        )
    elif share < IDEAL_HEIGHT_SHARE[0]:
        instructions.append(
            Instruction(
                Severity.ADVISORY, "Step closer so you fill more of the frame.", "too_small"
            )
        )

    if abs(offset) > CENTRE_TOLERANCE:
        direction = "right" if offset < 0 else "left"
        instructions.append(
            Instruction(
                Severity.ADVISORY,
                f"Move a little to your {direction} so you are centred in the frame.",
                "off_centre",
            )
        )

    brightness = _brightness(image)
    if brightness < DARK_THRESHOLD:
        instructions.append(
            Instruction(Severity.ADVISORY, "Turn on more light, or face a window.", "too_dark")
        )
    elif brightness > BRIGHT_THRESHOLD:
        instructions.append(
            Instruction(
                Severity.ADVISORY,
                "The photo is blown out. Move away from the direct light behind you.",
                "too_bright",
            )
        )

    if confidence < 0.35:
        instructions.append(
            Instruction(
                Severity.ADVISORY,
                "You blend into the background. Stand against a plainer wall, or wear something "
                "a different colour from it.",
                "poor_separation",
            )
        )

    if _looks_like_loose_clothing(mask):
        instructions.append(
            Instruction(
                Severity.ADVISORY,
                "Loose clothing reads as a larger body. Close-fitting clothes measure better.",
                "loose_clothing",
            )
        )

    instructions.sort(key=lambda i: 0 if i.blocking else 1)
    usable = not any(i.blocking for i in instructions)
    return CaptureGuidance(view, usable, _framing_score(share, offset), instructions)


def _brightness(image: np.ndarray) -> float:
    values = image[:, :, :3].astype(np.float64) if image.ndim == 3 else image.astype(np.float64)
    values = values / 255.0 if values.max() > 1.5 else values
    return float(values.mean())


def _framing_score(share: float, offset: float) -> float:
    """How well framed the shot is, 0 to 1, independent of any single warning."""
    low, high = IDEAL_HEIGHT_SHARE
    if share < low:
        height_score = max(0.0, share / low)
    elif share > high:
        height_score = max(0.0, 1.0 - (share - high) / (1.0 - high))
    else:
        height_score = 1.0
    centre_score = max(0.0, 1.0 - abs(offset) / (CENTRE_TOLERANCE * 2.5))
    return float(np.clip(0.7 * height_score + 0.3 * centre_score, 0.0, 1.0))


def _looks_like_loose_clothing(mask: np.ndarray) -> bool:
    """A torso much wider than the hips suggests fabric rather than a body.

    Crude on purpose. It only ever raises an advisory, so a false positive
    costs a sentence and a false negative costs nothing that the measurement
    warnings do not already say.
    """
    top, bottom = vertical_extent(mask)
    span = bottom - top
    if span < 20:
        return False
    widths = mask.sum(axis=1).astype(np.float64)
    waist = widths[top + int(span * 0.42) : top + int(span * 0.52)]
    hip = widths[top + int(span * 0.52) : top + int(span * 0.62)]
    if waist.size == 0 or hip.size == 0 or hip.mean() <= 0:
        return False
    return bool(waist.mean() / hip.mean() > 1.22)


def overall_guidance(views: dict[str, CaptureGuidance]) -> list[str]:
    """What to say about the whole set, once each view has been judged."""
    messages: list[str] = []
    if "front" not in views or not views["front"].usable:
        messages.append("A usable front photo is required before an avatar can be built.")
    if "side" not in views:
        messages.append(
            "Add a side photo. Without one, depth is inferred from proportion rather than measured."
        )
    return messages
