"""Pose recovery from photographs.

The detector is a port. The solver that turns landmarks into joint rotations
is ours, is pure numpy, and runs without any model present.
"""

from sveyra_human.pose.landmarks import INDEX, NAMES, Landmarks
from sveyra_human.pose.ports import PoseSource
from sveyra_human.pose.solver import OBSERVED, BoneObservation, SolvedPose, solve_pose

__all__ = [
    "INDEX",
    "NAMES",
    "OBSERVED",
    "BoneObservation",
    "Landmarks",
    "PoseSource",
    "SolvedPose",
    "solve_pose",
]
