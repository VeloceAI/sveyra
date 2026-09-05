"""Round-trip: pose a skeleton, read landmarks off it, recover the pose.

Comparing Euler angles would be the wrong test. A bone direction leaves the
twist about that direction undetermined, so the solver is free to return a
different triple that puts the limb in the same place. What must match is where
the joints end up, which is the thing a viewer and a garment fitter both care
about.
"""

from __future__ import annotations

import numpy as np
import pytest

from sveyra_human.body.parameters import BodyParameters
from sveyra_human.pose import Landmarks, solve_pose
from sveyra_human.pose.landmarks import NAMES
from sveyra_human.pose.ports import MissingPoseSource, PoseSource
from sveyra_human.skeleton.joints import HIERARCHY
from sveyra_human.skeleton.model import build_skeleton

# Which joint each landmark sits on. Only the ones the solver reads.
LANDMARK_AT = {
    "left_shoulder": "upperarm_L",
    "right_shoulder": "upperarm_R",
    "left_elbow": "forearm_L",
    "right_elbow": "forearm_R",
    "left_wrist": "hand_L",
    "right_wrist": "hand_R",
    "left_hip": "thigh_L",
    "right_hip": "thigh_R",
    "left_knee": "calf_L",
    "right_knee": "calf_R",
    "left_ankle": "foot_L",
    "right_ankle": "foot_R",
}


def _euler_xyz(x: float, y: float, z: float) -> np.ndarray:
    cx, sx = np.cos(x), np.sin(x)
    cy, sy = np.cos(y), np.sin(y)
    cz, sz = np.cos(z), np.sin(z)
    rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return rx @ ry @ rz


def forward_kinematics(skeleton, rotations):
    """World joint positions for a pose, walking parents before children."""
    world_rot = {"root": np.eye(3)}
    world_pos = {"root": skeleton.positions["root"].copy()}
    for joint, parent in HIERARCHY.items():
        if parent is None:
            continue
        rest_offset = skeleton.positions[joint] - skeleton.positions[parent]
        local = _euler_xyz(*rotations.get(joint, (0.0, 0.0, 0.0)))
        world_pos[joint] = world_pos[parent] + world_rot[parent] @ rest_offset
        world_rot[joint] = world_rot[parent] @ local
    return world_pos


def landmarks_from(skeleton, rotations) -> Landmarks:
    """Synthesise a perfect detection of a posed body."""
    joints = forward_kinematics(skeleton, rotations)
    points = np.zeros((33, 3))
    visibility = np.zeros(33)
    for name, joint in LANDMARK_AT.items():
        points[NAMES.index(name)] = joints[joint]
        visibility[NAMES.index(name)] = 1.0

    # Landmarks with no joint of their own, placed off ones that have.
    head = joints["head"]
    neck = joints["neck"]
    for name, position in (
        ("nose", head + np.array([0.0, 2.0, 8.0])),
        ("left_ear", neck + np.array([6.0, 8.0, 0.0])),
        ("right_ear", neck + np.array([-6.0, 8.0, 0.0])),
        ("left_index", joints["hand_L"] + (joints["hand_L"] - joints["forearm_L"]) * 0.3),
        ("right_index", joints["hand_R"] + (joints["hand_R"] - joints["forearm_R"]) * 0.3),
        ("left_foot_index", joints["foot_L"] + np.array([0.0, -2.0, 12.0])),
        ("right_foot_index", joints["foot_R"] + np.array([0.0, -2.0, 12.0])),
    ):
        points[NAMES.index(name)] = position
        visibility[NAMES.index(name)] = 1.0
    return Landmarks(points=points, visibility=visibility)


@pytest.fixture
def skeleton():
    return build_skeleton(BodyParameters(height=170.0))


def test_rest_pose_recovers_as_rest(skeleton):
    """A body standing exactly at rest must come back with no rotation."""
    result = solve_pose(landmarks_from(skeleton, {}), skeleton)
    joints = forward_kinematics(skeleton, result.rotations)
    for name in LANDMARK_AT.values():
        assert np.allclose(joints[name], skeleton.positions[name], atol=0.5), name


@pytest.mark.parametrize(
    "pose",
    [
        pytest.param({"forearm_L": (0.0, -1.0, 0.0)}, id="left elbow bent"),
        pytest.param({"upperarm_L": (0.0, 0.0, -0.6)}, id="left arm lowered"),
        pytest.param({"calf_R": (0.9, 0.0, 0.0)}, id="right knee bent"),
        pytest.param(
            {"upperarm_R": (0.0, 0.0, 0.5), "forearm_R": (0.0, -0.8, 0.0)},
            id="right arm raised and bent",
        ),
        pytest.param(
            {"thigh_L": (-0.5, 0.0, 0.0), "calf_L": (0.7, 0.0, 0.0)},
            id="left leg stepping",
        ),
    ],
)
def test_recovers_joint_positions(skeleton, pose):
    """The solved pose must put every joint where the original pose had it."""
    truth = forward_kinematics(skeleton, pose)
    result = solve_pose(landmarks_from(skeleton, pose), skeleton)
    recovered = forward_kinematics(skeleton, result.rotations)

    for name in LANDMARK_AT.values():
        error = float(np.linalg.norm(recovered[name] - truth[name]))
        assert error < 1.0, f"{name} off by {error:.2f} cm"


def test_reports_what_it_could_not_see(skeleton):
    """A joint whose landmarks are hidden is named, not silently left at rest."""
    lm = landmarks_from(skeleton, {})
    lm.visibility[NAMES.index("left_elbow")] = 0.1

    result = solve_pose(lm, skeleton)

    assert "forearm_L" in result.unseen
    assert "upperarm_L" in result.unseen
    assert "forearm_L" not in result.rotations
    assert result.coverage < 1.0


def test_impossible_input_is_clamped_and_named(skeleton):
    """An elbow driven backward comes back straight, and says it was clamped."""
    lm = landmarks_from(skeleton, {"forearm_L": (0.0, 1.2, 0.0)})

    result = solve_pose(lm, skeleton)

    flex = result.rotations["forearm_L"][1]
    assert flex <= 1e-6, f"elbow bent backward to {flex}"
    assert "forearm_L" in result.clamped


def test_missing_detector_refuses_rather_than_inventing():
    source = MissingPoseSource()
    assert isinstance(source, PoseSource)
    with pytest.raises(RuntimeError, match="No pose detector"):
        source.detect(np.zeros((4, 4, 3)))
