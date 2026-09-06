"""Rejecting inputs the engine cannot honestly use."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from sveyra_human.vision.silhouette import is_full_body

MIN_DIMENSION = 96


@dataclass
class CaptureIssue:
    view: str
    message: str
    fatal: bool = False


@dataclass
class CaptureReport:
    issues: list[CaptureIssue] = field(default_factory=list)

    @property
    def usable(self) -> bool:
        return not any(issue.fatal for issue in self.issues)

    def warnings(self) -> list[str]:
        return [f"{i.view}: {i.message}" for i in self.issues if not i.fatal]

    def errors(self) -> list[str]:
        return [f"{i.view}: {i.message}" for i in self.issues if i.fatal]


def validate_view(
    view: str, image: np.ndarray, mask: np.ndarray, confidence: float
) -> list[CaptureIssue]:
    issues: list[CaptureIssue] = []
    if min(image.shape[:2]) < MIN_DIMENSION:
        issues.append(CaptureIssue(view, f"image is smaller than {MIN_DIMENSION}px", fatal=True))
    if not mask.any():
        issues.append(CaptureIssue(view, "no person was found", fatal=True))
        return issues
    if not is_full_body(mask):
        issues.append(
            CaptureIssue(
                view,
                "the subject does not span enough of the frame to scale by height",
                fatal=True,
            )
        )
    if confidence < 0.35:
        issues.append(
            CaptureIssue(view, "the subject separates poorly from the background")
        )
    if mask.mean() > 0.55:
        issues.append(CaptureIssue(view, "the subject fills most of the frame; step back"))
    return issues
