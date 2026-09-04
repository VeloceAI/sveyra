"""Face parameters, fitting and head shaping.

Geometry carries proportion; identity comes mostly from texture. The model is
deliberately coarse because a fitted mesh cannot capture a likeness on its own.
"""

from sveyra_human.face.deformation import apply_face_shape, width_profile
from sveyra_human.face.fitter import fit_face_parameters, landmarks_from_parameters
from sveyra_human.face.parameters import FaceParameters, neutral_fractions

__all__ = [
    "FaceParameters",
    "apply_face_shape",
    "fit_face_parameters",
    "landmarks_from_parameters",
    "neutral_fractions",
    "width_profile",
]
