"""Recovering face parameters from landmarks.

Landmarks are normalised image points, so nothing here knows about pixels or
cameras beyond the scale factor a caller supplies. That keeps the fitter usable
with MediaPipe, with a different landmarker, or with synthetic points from a
test.

Measurements come straight from distances between named landmarks. A face is
small and landmarks are dense, so an iterative solver would be pure ceremony:
the mapping from points to widths is direct.
"""

from __future__ import annotations

import numpy as np

from sveyra_human.api.errors import ReconstructionError
from sveyra_human.face.parameters import PLAUSIBLE_SCALE, FaceParameters
from sveyra_human.vision.port import PoseLandmarks

# Landmarks the fitter needs, and what each pair measures.
REQUIRED = ("chin", "hairline")

_WIDTH_PAIRS: dict[str, tuple[str, str]] = {
    "face_width": ("face_left", "face_right"),
    "forehead_width": ("forehead_left", "forehead_right"),
    "cheekbone_width": ("cheek_left", "cheek_right"),
    "jaw_width": ("jaw_left", "jaw_right"),
    "chin_width": ("chin_left", "chin_right"),
    "eye_spacing": ("eye_inner_left", "eye_inner_right"),
    "eye_width": ("eye_outer_left", "eye_inner_left"),
    "mouth_width": ("mouth_left", "mouth_right"),
    "nose_width": ("nose_left", "nose_right"),
}


def _point(landmarks: PoseLandmarks, name: str) -> np.ndarray | None:
    landmark = landmarks.get(name)
    if landmark is None or landmark.visibility < 0.25:
        return None
    return np.array([landmark.x, landmark.y])


def fit_face_parameters(
    landmarks: PoseLandmarks,
    *,
    face_length_cm: float | None = None,
    pixels_per_cm: float | None = None,
    image_height_px: int | None = None,
) -> FaceParameters:
    """Turn landmarks into a `FaceParameters`.

    Scale comes from `face_length_cm` when known, since a face in an image has
    no absolute size. Otherwise `pixels_per_cm` and `image_height_px` are used.
    Supplying neither is an error rather than a guess.
    """
    chin = _point(landmarks, "chin")
    hairline = _point(landmarks, "hairline")
    if chin is None or hairline is None:
        raise ReconstructionError(
            f"face fitting needs the {' and '.join(REQUIRED)} landmarks"
        )

    span_normalised = float(np.linalg.norm(chin - hairline))
    if span_normalised < 1e-6:
        raise ReconstructionError("chin and hairline landmarks coincide")

    if face_length_cm is not None:
        length = float(face_length_cm)
        scale = length / span_normalised
    elif pixels_per_cm and image_height_px:
        scale = image_height_px / pixels_per_cm
        length = span_normalised * scale
    else:
        raise ValueError("supply either face_length_cm or pixels_per_cm with image_height_px")

    measured: dict[str, float] = {}
    for field_name, (a, b) in _WIDTH_PAIRS.items():
        pa, pb = _point(landmarks, a), _point(landmarks, b)
        if pa is None or pb is None:
            continue
        measured[field_name] = float(np.linalg.norm(pa - pb)) * scale

    nose_tip = _point(landmarks, "nose_tip")
    nose_bridge = _point(landmarks, "nose_bridge")
    if nose_tip is not None and nose_bridge is not None:
        measured["nose_length"] = float(np.linalg.norm(nose_tip - nose_bridge)) * scale

    params = FaceParameters(face_length=length)
    neutral = FaceParameters(face_length=length)
    for name, value in measured.items():
        reference = float(getattr(neutral, name))
        low, high = reference * PLAUSIBLE_SCALE[0], reference * PLAUSIBLE_SCALE[1]
        # A landmark that wandered gives a measurement no face could have.
        # Clamping keeps one bad point from distorting the whole face.
        setattr(params, name, float(np.clip(value, low, high)))
    return params


def landmarks_from_parameters(
    params: FaceParameters, *, jitter: float = 0.0, seed: int = 0
) -> PoseLandmarks:
    """The inverse of the fitter, for testing.

    Generates the landmark set a perfect detector would produce for a known
    face, so recovery can be measured rather than eyeballed. `jitter` adds
    normalised noise to simulate a detector that is merely good.
    """
    from sveyra_human.vision.port import Landmark

    rng = np.random.default_rng(seed)
    length = float(params.face_length)
    # Place the face in a unit box: chin at the bottom, hairline at the top.
    top, bottom = 0.1, 0.9
    span = bottom - top

    def to_norm(cm: float) -> float:
        return cm / length * span

    def at(x_cm: float, height_fraction: float) -> tuple[float, float]:
        return 0.5 + to_norm(x_cm), bottom - height_fraction * span

    points: dict[str, tuple[float, float]] = {
        "chin": (0.5, bottom),
        "hairline": (0.5, top),
        "face_left": at(-float(params.face_width) / 2, 0.5),
        "face_right": at(float(params.face_width) / 2, 0.5),
        "forehead_left": at(-float(params.forehead_width) / 2, 0.8),
        "forehead_right": at(float(params.forehead_width) / 2, 0.8),
        "cheek_left": at(-float(params.cheekbone_width) / 2, 0.55),
        "cheek_right": at(float(params.cheekbone_width) / 2, 0.55),
        "jaw_left": at(-float(params.jaw_width) / 2, 0.22),
        "jaw_right": at(float(params.jaw_width) / 2, 0.22),
        "chin_left": at(-float(params.chin_width) / 2, 0.06),
        "chin_right": at(float(params.chin_width) / 2, 0.06),
        "eye_inner_left": at(-float(params.eye_spacing) / 2, 0.52),
        "eye_inner_right": at(float(params.eye_spacing) / 2, 0.52),
        "eye_outer_left": at(
            -float(params.eye_spacing) / 2 - float(params.eye_width), 0.52
        ),
        "eye_outer_right": at(
            float(params.eye_spacing) / 2 + float(params.eye_width), 0.52
        ),
        "mouth_left": at(-float(params.mouth_width) / 2, 0.26),
        "mouth_right": at(float(params.mouth_width) / 2, 0.26),
        "nose_left": at(-float(params.nose_width) / 2, 0.36),
        "nose_right": at(float(params.nose_width) / 2, 0.36),
        "nose_bridge": at(0.0, 0.52),
        "nose_tip": at(0.0, 0.52 - to_norm(float(params.nose_length)) / span),
    }

    built = {}
    for name, (x, y) in points.items():
        if jitter:
            x += float(rng.normal(0.0, jitter))
            y += float(rng.normal(0.0, jitter))
        built[name] = Landmark(name=name, x=x, y=y, visibility=1.0)
    return PoseLandmarks(points=built)
