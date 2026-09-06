"""Skinning, posing, and skinned export."""

import numpy as np
import pygltflib
import pytest

from sveyra_human import BodyParameters, SveyraHumanEngine
from sveyra_human.body.cage import build_cage
from sveyra_human.body.mesh_deformer import cage_to_mesh
from sveyra_human.rig import (
    MAX_INFLUENCES,
    blend,
    compute_skin_weights,
    dual_quaternion,
    effective_parent,
    inverse_bind_matrices,
    joint_order,
    local_translations,
    quaternion_from_axis_angle,
    transform_point,
    validate_weights,
)
from sveyra_human.skeleton.model import build_skeleton


@pytest.fixture
def rigged():
    params = BodyParameters(height=180.0)
    skeleton = build_skeleton(params)
    mesh = cage_to_mesh(build_cage(params, skeleton.positions), subdivisions=0)
    indices, weights, names = compute_skin_weights(mesh.vertices, skeleton)
    return params, skeleton, mesh, indices, weights, names


# -- weights -------------------------------------------------------------


def test_every_vertex_is_fully_weighted(rigged) -> None:
    _, _, mesh, indices, weights, names = rigged
    validate_weights(indices, weights, len(names))
    assert weights.shape == (mesh.vertex_count, MAX_INFLUENCES)
    assert np.allclose(weights.sum(axis=1), 1.0, atol=1e-4)
    assert (weights >= 0).all()


def test_weights_follow_anatomy(rigged) -> None:
    """A vertex out at the hand must not be driven by a leg."""
    _, _, mesh, indices, weights, names = rigged
    for picker, expected in (
        (np.argmax(mesh.vertices[:, 0]), ("hand_L", "forearm_L")),
        (np.argmin(mesh.vertices[:, 0]), ("hand_R", "forearm_R")),
        (np.argmin(mesh.vertices[:, 1]), ("foot_L", "foot_R", "calf_L", "calf_R")),
        (np.argmax(mesh.vertices[:, 1]), ("head", "neck")),
    ):
        vertex = int(picker)
        dominant = names[indices[vertex][int(np.argmax(weights[vertex]))]]
        assert dominant in expected, dominant


def test_a_stiffer_falloff_concentrates_influence(rigged) -> None:
    _, skeleton, mesh, _, _, _ = rigged
    _, soft, _ = compute_skin_weights(mesh.vertices, skeleton, falloff=1.2)
    _, stiff, _ = compute_skin_weights(mesh.vertices, skeleton, falloff=5.0)
    assert stiff.max(axis=1).mean() > soft.max(axis=1).mean()


def test_validate_weights_catches_a_bad_rig() -> None:
    with pytest.raises(ValueError):
        validate_weights(
            np.zeros((3, MAX_INFLUENCES), np.uint16), np.zeros((3, MAX_INFLUENCES)), 5
        )
    with pytest.raises(ValueError):
        validate_weights(
            np.full((2, MAX_INFLUENCES), 99, np.uint16),
            np.full((2, MAX_INFLUENCES), 0.25),
            5,
        )


# -- skeleton for the renderer -------------------------------------------


def test_joint_order_lists_parents_before_children() -> None:
    order = joint_order()
    for index, joint in enumerate(order):
        parent = effective_parent(joint, order)
        if parent is not None:
            assert order.index(parent) < index, joint


def test_local_translations_reconstruct_world_positions(rigged) -> None:
    _, skeleton, _, _, _, _ = rigged
    order = joint_order()
    local = local_translations(skeleton, order)
    world: dict[str, np.ndarray] = {}
    for joint in order:
        parent = effective_parent(joint, order)
        base = world[parent] if parent else np.zeros(3)
        world[joint] = base + local[joint]
    for joint in order:
        assert np.allclose(world[joint], skeleton.positions[joint] * 0.01, atol=1e-5), joint


def test_inverse_bind_matrices_move_a_joint_to_the_origin(rigged) -> None:
    _, skeleton, _, _, _, _ = rigged
    order = joint_order()
    matrices = inverse_bind_matrices(skeleton, order)
    for i, joint in enumerate(order):
        point = np.append(skeleton.positions[joint] * 0.01, 1.0)
        assert np.allclose((matrices[i] @ point)[:3], 0.0, atol=1e-5), joint


# -- dual quaternion skinning --------------------------------------------


def test_an_identity_transform_leaves_a_point_alone() -> None:
    dq = dual_quaternion(np.array([1.0, 0.0, 0.0, 0.0]), np.zeros(3))
    point = np.array([0.3, 1.2, -0.4])
    assert np.allclose(transform_point(dq, point), point, atol=1e-9)


def test_a_quarter_turn_about_y_maps_x_onto_minus_z() -> None:
    rotation = quaternion_from_axis_angle(np.array([0.0, 1.0, 0.0]), np.pi / 2)
    dq = dual_quaternion(rotation, np.zeros(3))
    moved = transform_point(dq, np.array([1.0, 0.0, 0.0]))
    assert np.allclose(moved, [0.0, 0.0, -1.0], atol=1e-6)


def test_translation_is_applied() -> None:
    dq = dual_quaternion(np.array([1.0, 0.0, 0.0, 0.0]), np.array([0.0, 0.5, 0.0]))
    assert np.allclose(transform_point(dq, np.zeros(3)), [0.0, 0.5, 0.0], atol=1e-9)


def test_blending_two_identical_transforms_changes_nothing() -> None:
    dq = dual_quaternion(
        quaternion_from_axis_angle(np.array([1.0, 0.0, 0.0]), 0.7), np.array([0.1, 0.2, 0.3])
    )
    blended = blend(np.stack([dq, dq]), np.array([0.5, 0.5]))
    point = np.array([0.2, -0.4, 0.9])
    assert np.allclose(transform_point(blended, point), transform_point(dq, point), atol=1e-9)


def test_blending_handles_opposite_quaternion_signs() -> None:
    """q and -q are the same rotation; blending them naively cancels to nothing."""
    rotation = quaternion_from_axis_angle(np.array([0.0, 0.0, 1.0]), 1.1)
    a = dual_quaternion(rotation, np.zeros(3))
    b = dual_quaternion(-rotation, np.zeros(3))
    blended = blend(np.stack([a, b]), np.array([0.5, 0.5]))
    point = np.array([1.0, 0.0, 0.0])
    assert np.allclose(transform_point(blended, point), transform_point(a, point), atol=1e-6)


def test_a_blended_rotation_preserves_length() -> None:
    """Volume preservation is the reason for dual quaternions over linear blending."""
    first = dual_quaternion(
        quaternion_from_axis_angle(np.array([0.0, 1.0, 0.0]), 0.0), np.zeros(3)
    )
    second = dual_quaternion(
        quaternion_from_axis_angle(np.array([0.0, 1.0, 0.0]), np.pi / 2), np.zeros(3)
    )
    blended = blend(np.stack([first, second]), np.array([0.5, 0.5]))
    point = np.array([1.0, 0.0, 0.0])
    assert np.linalg.norm(transform_point(blended, point)) == pytest.approx(1.0, abs=1e-6)


# -- skinned export ------------------------------------------------------


def test_the_exported_glb_carries_a_usable_skin(tmp_path) -> None:
    artifact = SveyraHumanEngine("draft").build_parametric(BodyParameters(height=184.0))
    path = artifact.export(tmp_path / "rigged.glb")

    gltf = pygltflib.GLTF2().load(str(path))
    assert len(gltf.skins) == 1
    skin = gltf.skins[0]
    assert len(skin.joints) == len(joint_order())

    primitive = gltf.meshes[0].primitives[0]
    assert primitive.attributes.JOINTS_0 is not None
    assert primitive.attributes.WEIGHTS_0 is not None

    assert gltf.accessors[skin.inverseBindMatrices].count == len(skin.joints)
    assert gltf.accessors[skin.inverseBindMatrices].type == pygltflib.MAT4
    # Every joint index must point at a real node.
    assert all(0 <= j < len(gltf.nodes) for j in skin.joints)


def test_exporting_unrigged_is_still_possible(tmp_path) -> None:
    artifact = SveyraHumanEngine("draft").build_parametric(BodyParameters(height=170.0))
    path = artifact.export(tmp_path / "static.glb", rigged=False)
    gltf = pygltflib.GLTF2().load(str(path))
    assert not gltf.skins


def test_the_rigged_export_is_still_in_metres(tmp_path) -> None:
    artifact = SveyraHumanEngine("draft").build_parametric(BodyParameters(height=180.0))
    path = artifact.export(tmp_path / "rigged.glb")
    gltf = pygltflib.GLTF2().load(str(path))
    assert gltf.accessors[0].max[1] == pytest.approx(1.80, abs=0.01)
