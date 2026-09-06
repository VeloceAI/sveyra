"""The seam between the engine and whatever detects landmarks.

MediaPipe's BlazePose is the obvious first adapter, but it is a large binary
dependency and it is not the only detector that emits these 33 points. Keeping
it behind a protocol means the solver, which is the part worth owning, can be
tested and shipped without it.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np

from sveyra_human.pose.landmarks import Landmarks


@runtime_checkable
class PoseSource(Protocol):
    """Detects body landmarks in a photograph."""

    name: str

    def detect(self, image: np.ndarray) -> Landmarks | None:
        """Return landmarks, or None when no person was found.

        Returning None is the honest answer for a photo with no subject in it.
        Callers must handle it rather than receiving a pose of zeros.
        """
        ...


class MissingPoseSource:
    """The default: refuses rather than inventing a pose.

    An engine with no detector installed should say so at the point of use. A
    stub that returned a T-pose would let a caller believe a photograph had
    been read when nothing looked at it.
    """

    name = "missing"

    def detect(self, image: np.ndarray) -> Landmarks | None:
        raise RuntimeError(
            "No pose detector is configured. Install one and pass it as the "
            "PoseSource, for example a MediaPipe BlazePose adapter."
        )
