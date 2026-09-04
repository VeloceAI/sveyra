"""Topology is a contract, not an implementation detail.

Garment transfer, morph targets, shared UVs and blend shapes all rest on every
avatar having the same vertices in the same order with the same connectivity.
Nothing else in the suite guards that, so it is guarded here: if a change to
cage resolution or lofting silently alters topology, these fail rather than
quietly breaking every garment fitted against the old mesh.
"""

import numpy as np
import pytest

from sveyra_human import BodyParameters, SveyraHumanEngine
from sveyra_human.body.cage import build_cage
from sveyra_human.body.mesh_deformer import cage_to_mesh, vertex_part_map
from sveyra_human.rig import compute_skin_weights, joint_order
from sveyra_human.skeleton.model import build_skeleton

# The shape of a SVEYRA human at each quality. Changing any of these is a
# breaking change for anything fitted against the old topology.
EXPECTED = {
    "draft": (924, 1692),
    "balanced": (3528, 6768),
    "high": (13812, 27072),
}

EXTREMES = [
    ("tiny", BodyParameters(height=150.0)),
    ("tall", BodyParameters(height=205.0)),
    ("broad", BodyParameters(height=175.0, chest_width=55.0, waist_width=52.0, hip_width=50.0)),
    ("slim", BodyParameters(height=190.0, chest_width=30.0, waist_width=24.0, hip_width=28.0)),
]


def mesh_for(params: BodyParameters, quality: str = "balanced", with_uv: bool = True):
    return SveyraHumanEngine(quality).build_parametric(params, with_uv=with_uv)._mesh


@pytest.mark.parametrize(("quality", "counts"), list(EXPECTED.items()))
def test_each_quality_has_a_fixed_shape(quality: str, counts: tuple[int, int]) -> None:
    mesh = mesh_for(BodyParameters(height=180.0), quality)
    assert (mesh.vertex_count, mesh.face_count) == counts


def test_every_body_shares_one_topology() -> None:
    """The property garment transfer depends on."""
    reference = mesh_for(EXTREMES[0][1])
    for label, params in EXTREMES[1:]:
        mesh = mesh_for(params)
        assert mesh.vertex_count == reference.vertex_count, label
        assert np.array_equal(mesh.faces, reference.faces), label


def test_uvs_are_shared_across_bodies() -> None:
    """One texture atlas layout for everyone, so garments and decals transfer."""
    reference = mesh_for(EXTREMES[0][1])
    for label, params in EXTREMES[1:]:
        assert np.array_equal(mesh_for(params).uv, reference.uv), label


def test_a_vertex_keeps_its_meaning_across_bodies() -> None:
    """Vertex N is the same anatomical location on every avatar.

    This is what makes a garment vertex correspondence valid at all. Checked
    against the cage part a vertex came from, which is exact, rather than
    against the bone it binds to, which is a proxy that drifts at part
    boundaries when proportions change.
    """
    reference = None
    for label, params in EXTREMES:
        cage = build_cage(params, build_skeleton(params).positions)
        parts = vertex_part_map(cage, subdivisions=1)
        if reference is None:
            reference = parts
        else:
            assert parts == reference, label


@pytest.mark.parametrize("subdivisions", [0, 1, 2])
def test_the_part_map_covers_every_vertex(subdivisions: int) -> None:
    params = BodyParameters(height=180.0)
    cage = build_cage(params, build_skeleton(params).positions)
    mesh = cage_to_mesh(cage, subdivisions=subdivisions)
    assert len(vertex_part_map(cage, subdivisions=subdivisions)) == mesh.vertex_count


def test_bone_binding_is_stable_but_not_exact_at_boundaries() -> None:
    """Documents a real limit rather than asserting a guarantee that does not hold.

    Skin weights come from distance, so a vertex near the shoulder can bind to
    the chest on one body and the upper arm on another. Correspondence by part
    is exact; correspondence by bone is about 86 percent on extreme bodies.
    """
    dominant = []
    for _, params in EXTREMES:
        skeleton = build_skeleton(params)
        mesh = cage_to_mesh(build_cage(params, skeleton.positions), subdivisions=0)
        indices, weights, names = compute_skin_weights(mesh.vertices, skeleton)
        dominant.append(
            [names[indices[i][int(np.argmax(weights[i]))]] for i in range(0, 900, 25)]
        )

    for other in dominant[1:]:
        agreement = sum(a == b for a, b in zip(dominant[0], other, strict=True)) / len(other)
        assert agreement > 0.8


def test_the_joint_set_is_fixed() -> None:
    order = joint_order()
    assert len(order) == 18
    for _, params in EXTREMES:
        skeleton = build_skeleton(params)
        assert all(name in skeleton.positions for name in order)


def test_subdivision_relates_the_qualities_predictably() -> None:
    """Each level is a 4-to-1 split, so counts must follow."""
    draft_v, draft_f = EXPECTED["draft"]
    balanced_v, balanced_f = EXPECTED["balanced"]
    high_v, high_f = EXPECTED["high"]
    assert balanced_f == draft_f * 4
    assert high_f == balanced_f * 4
    assert balanced_v > draft_v and high_v > balanced_v


def test_topology_does_not_depend_on_the_fitting_route() -> None:
    """A fitted body and a parametric one must be interchangeable downstream."""
    from sveyra_human.camera.projection import OrthographicCamera, rasterise_silhouette

    truth = BodyParameters(height=178.0, waist_width=34.0)
    engine = SveyraHumanEngine("draft")
    direct = engine.build_parametric(truth)._mesh

    views = {
        view: rasterise_silhouette(
            direct.vertices,
            direct.faces,
            OrthographicCamera.fit_to_height(view, truth.height, 200, 320),
        )
        for view in ("front", "side")
    }
    fitted = engine.build_from_silhouettes(views, height_cm=truth.height)._mesh

    assert fitted.vertex_count == direct.vertex_count
    assert np.array_equal(fitted.faces, direct.faces)
