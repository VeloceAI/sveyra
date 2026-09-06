"""Skinning and posing."""

from sveyra_human.rig.dqs import blend, dual_quaternion, quaternion_from_axis_angle, transform_point
from sveyra_human.rig.skeleton import (
    effective_parent,
    inverse_bind_matrices,
    joint_order,
    local_translations,
)
from sveyra_human.rig.weights import (
    DEFORMING_BONES,
    MAX_INFLUENCES,
    compute_skin_weights,
    validate_weights,
)

__all__ = [
    "DEFORMING_BONES",
    "MAX_INFLUENCES",
    "blend",
    "compute_skin_weights",
    "dual_quaternion",
    "effective_parent",
    "inverse_bind_matrices",
    "joint_order",
    "local_translations",
    "quaternion_from_axis_angle",
    "transform_point",
    "validate_weights",
]
