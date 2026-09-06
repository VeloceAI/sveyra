"""Geometry: cross sections, skeleton, cage and surface."""

import numpy as np
import pytest

from sveyra_human.body.anatomy import section_girth
from sveyra_human.body.cage import build_cage
from sveyra_human.body.cross_sections import CrossSection, resample, torso_profile
from sveyra_human.body.mesh_deformer import cage_to_mesh, subdivide
from sveyra_human.body.parameters import BodyParameters
from sveyra_human.skeleton.joints import HIERARCHY, is_valid_hierarchy
from sveyra_human.skeleton.model import build_skeleton


@pytest.fixture
def params() -> BodyParameters:
    return BodyParameters(height=180.0)


# -- cross sections ------------------------------------------------------


def test_outline_has_the_requested_number_of_points() -> None:
    assert CrossSection(0.0, 30.0, 20.0).outline(24).shape == (24, 3)


def test_outline_respects_width_and_depth() -> None:
    outline = CrossSection(5.0, 30.0, 20.0, exponent=2.0).outline(64)
    assert outline[:, 0].max() == pytest.approx(15.0, abs=1e-6)
    assert outline[:, 2].max() == pytest.approx(10.0, abs=1e-6)
    assert np.allclose(outline[:, 1], 5.0)


def test_a_circular_section_has_a_circular_perimeter() -> None:
    # Exponent 2 with equal width and depth is a circle, so the numerical
    # girth must agree with pi*d. This is what validates section_girth.
    girth = section_girth(CrossSection(0.0, 20.0, 20.0, exponent=2.0), samples=512)
    assert girth == pytest.approx(np.pi * 20.0, rel=1e-3)


def test_a_squarer_exponent_increases_girth() -> None:
    ellipse = section_girth(CrossSection(0.0, 20.0, 14.0, exponent=2.0))
    squarer = section_girth(CrossSection(0.0, 20.0, 14.0, exponent=4.0))
    assert squarer > ellipse


def test_resample_spans_the_profile_and_hits_the_count(params: BodyParameters) -> None:
    profile = torso_profile(params)
    out = resample(profile, 14)
    assert len(out) == 14
    assert out[0].y == pytest.approx(min(c.y for c in profile))
    assert out[-1].y == pytest.approx(max(c.y for c in profile))
    assert [c.y for c in out] == sorted(c.y for c in out)


def test_resample_rejects_degenerate_input(params: BodyParameters) -> None:
    with pytest.raises(ValueError):
        resample(torso_profile(params), 1)


# -- skeleton ------------------------------------------------------------


def test_hierarchy_is_well_formed() -> None:
    assert is_valid_hierarchy()


def test_every_joint_is_placed(params: BodyParameters) -> None:
    skeleton = build_skeleton(params)
    assert set(skeleton.positions) == set(HIERARCHY)


def test_skeleton_is_left_right_symmetric(params: BodyParameters) -> None:
    pos = build_skeleton(params).positions
    for name in ("upperarm", "forearm", "hand", "thigh", "calf", "foot"):
        left, right = pos[f"{name}_L"], pos[f"{name}_R"]
        assert left[0] == pytest.approx(-right[0])
        assert left[1] == pytest.approx(right[1])


def test_bone_lengths_follow_the_parameters(params: BodyParameters) -> None:
    skeleton = build_skeleton(params)
    assert skeleton.bone_length("forearm_L") == pytest.approx(
        float(params.upper_arm_length), rel=1e-6
    )
    assert skeleton.bone_length("root") == 0.0


def test_taller_people_get_longer_bones() -> None:
    short = build_skeleton(BodyParameters(height=160.0))
    tall = build_skeleton(BodyParameters(height=200.0))
    assert tall.bone_length("calf_L") > short.bone_length("calf_L")


# -- cage and surface ----------------------------------------------------


def test_cage_stays_small_enough_to_optimise(params: BodyParameters) -> None:
    cage = build_cage(params, build_skeleton(params).positions)
    # The design calls for a few hundred control vertices, not tens of thousands.
    assert 300 <= cage.vertex_count <= 1500


def test_cage_covers_every_body_part(params: BodyParameters) -> None:
    cage = build_cage(params, build_skeleton(params).positions)
    names = {p.name for p in cage.parts}
    expected = {"torso", "head"} | {
        f"{part}_{side}"
        for side in ("L", "R")
        for part in ("upperarm", "forearm", "thigh", "calf", "foot")
    }
    assert names == expected


def test_mesh_is_closed_enough_to_render(params: BodyParameters) -> None:
    cage = build_cage(params, build_skeleton(params).positions)
    mesh = cage_to_mesh(cage, subdivisions=0)
    assert mesh.vertex_count > 0
    assert mesh.face_count > 0
    assert int(mesh.faces.max()) < mesh.vertex_count


def test_normals_are_unit_length(params: BodyParameters) -> None:
    mesh = cage_to_mesh(build_cage(params, build_skeleton(params).positions), subdivisions=0)
    lengths = np.linalg.norm(mesh.normals(), axis=1)
    assert np.allclose(lengths, 1.0, atol=1e-4)


def test_subdivision_quadruples_faces_without_moving_the_surface(
    params: BodyParameters,
) -> None:
    mesh = cage_to_mesh(build_cage(params, build_skeleton(params).positions), subdivisions=0)
    finer = subdivide(mesh)
    assert finer.face_count == mesh.face_count * 4
    lo_a, hi_a = mesh.bounds()
    lo_b, hi_b = finer.bounds()
    assert np.allclose(lo_a, lo_b, atol=1e-3)
    assert np.allclose(hi_a, hi_b, atol=1e-3)


def test_limb_normals_point_outward(params: BodyParameters) -> None:
    """Inward-facing limbs are invisible under backface culling.

    The GLB exports with doubleSided false, so a flipped winding makes arms and
    legs render inside-out in any real viewer. Silhouette tests cannot catch
    this: an outline does not care which way a normal points.
    """
    from sveyra_human.body.mesh_deformer import vertex_part_map

    cage = build_cage(params, build_skeleton(params).positions)
    mesh = cage_to_mesh(cage, subdivisions=0)
    labels = np.array(vertex_part_map(cage, subdivisions=0))
    normals = mesh.normals()

    for part in ("torso", "head", "upperarm_L", "forearm_L", "thigh_L", "calf_L"):
        selected = np.where(labels == part)[0]
        points = mesh.vertices[selected]
        radial = points - points.mean(axis=0)
        lengths = np.linalg.norm(radial, axis=1, keepdims=True)
        lengths[lengths == 0] = 1.0
        outward = np.mean(np.einsum("ij,ij->i", normals[selected], radial / lengths) > 0)
        assert outward > 0.65, f"{part} normals point inward ({outward:.0%} outward)"


def test_limb_and_torso_windings_agree(params: BodyParameters) -> None:
    """One consistent surface orientation across the whole body."""
    from sveyra_human.body.mesh_deformer import vertex_part_map

    cage = build_cage(params, build_skeleton(params).positions)
    mesh = cage_to_mesh(cage, subdivisions=0)
    labels = np.array(vertex_part_map(cage, subdivisions=0))
    normals = mesh.normals()

    def outwardness(part: str) -> float:
        selected = np.where(labels == part)[0]
        points = mesh.vertices[selected]
        radial = points - points.mean(axis=0)
        lengths = np.linalg.norm(radial, axis=1, keepdims=True)
        lengths[lengths == 0] = 1.0
        return float(np.mean(np.einsum("ij,ij->i", normals[selected], radial / lengths) > 0))

    assert abs(outwardness("torso") - outwardness("thigh_L")) < 0.35
