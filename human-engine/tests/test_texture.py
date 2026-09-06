"""UV unwrapping and projective texturing."""

import numpy as np
import pytest

from sveyra_human import BodyParameters
from sveyra_human.body.cage import build_cage
from sveyra_human.body.mesh_deformer import cage_to_mesh
from sveyra_human.camera.projection import OrthographicCamera, rasterise_silhouette
from sveyra_human.skeleton.model import build_skeleton
from sveyra_human.texture import (
    build_uv_layout,
    cameras_for_views,
    project_views_to_texture,
    unwrap_cage,
)


@pytest.fixture
def cage():
    params = BodyParameters(height=180.0)
    return params, build_cage(params, build_skeleton(params).positions)


def photo(mesh, view, tint, height=180.0, res=(240, 384)):
    camera = OrthographicCamera.fit_to_height(view, height, *res)
    mask = rasterise_silhouette(mesh.vertices, mesh.faces, camera)
    image = np.full((*mask.shape, 3), (215, 212, 205), dtype=np.uint8)
    body = np.zeros((*mask.shape, 3), dtype=np.uint8)
    body[:, :] = tint
    return np.where(mask[:, :, None], body, image), camera


# -- unwrapping ----------------------------------------------------------


def test_every_part_gets_its_own_strip(cage) -> None:
    _, body_cage = cage
    layout = build_uv_layout(body_cage)
    assert set(layout) == {p.name for p in body_cage.parts}
    spans = sorted(layout.values())
    for (_, end), (start, _) in zip(spans, spans[1:], strict=False):
        assert start >= end - 1e-9, "part strips must not overlap"


def test_a_bigger_part_gets_a_taller_strip(cage) -> None:
    _, body_cage = cage
    layout = build_uv_layout(body_cage)
    torso = layout["torso"][1] - layout["torso"][0]
    foot = layout["foot_L"][1] - layout["foot_L"][0]
    assert torso > foot


def test_uvs_stay_inside_the_atlas(cage) -> None:
    _, body_cage = cage
    uv = unwrap_cage(body_cage)
    assert uv.shape[1] == 2
    assert uv.min() >= 0.0 and uv.max() <= 1.0


def test_there_is_one_uv_per_vertex_at_every_density(cage) -> None:
    _, body_cage = cage
    for subdivisions in (0, 1, 2):
        mesh = cage_to_mesh(body_cage, subdivisions=subdivisions, with_uv=True)
        assert mesh.uv is not None
        assert mesh.uv.shape[0] == mesh.vertex_count, subdivisions


def test_uvs_are_absent_unless_asked_for(cage) -> None:
    _, body_cage = cage
    assert cage_to_mesh(body_cage, subdivisions=0).uv is None


def test_an_empty_cage_is_rejected() -> None:
    from sveyra_human.body.cage import BodyCage

    with pytest.raises(ValueError):
        build_uv_layout(BodyCage(parts=[]))


# -- projection ----------------------------------------------------------


def test_a_texture_is_built_from_the_photographs(cage) -> None:
    params, body_cage = cage
    mesh = cage_to_mesh(body_cage, subdivisions=0, with_uv=True)
    views, cameras = {}, {}
    for view, tint in (("front", (200, 60, 60)), ("side", (60, 60, 200))):
        views[view], cameras[view] = photo(mesh, view, tint)

    texture = project_views_to_texture(mesh, mesh.uv, views, cameras, resolution=128)

    assert texture.albedo.shape == (128, 128, 3)
    assert texture.contributing_views == ["front", "side"]
    assert texture.covered_fraction() > 0.4


def test_the_front_photograph_actually_reaches_the_texture(cage) -> None:
    """A red subject must produce red texels, or nothing was sampled."""
    params, body_cage = cage
    mesh = cage_to_mesh(body_cage, subdivisions=0, with_uv=True)
    front, camera = photo(mesh, "front", (220, 40, 40))
    texture = project_views_to_texture(
        mesh, mesh.uv, {"front": front}, {"front": camera}, resolution=128
    )
    reddish = (texture.albedo[:, :, 0] > texture.albedo[:, :, 2] + 40).mean()
    assert reddish > 0.2


def test_coverage_records_what_was_inferred(cage) -> None:
    params, body_cage = cage
    mesh = cage_to_mesh(body_cage, subdivisions=0, with_uv=True)
    front, camera = photo(mesh, "front", (200, 60, 60))
    texture = project_views_to_texture(
        mesh, mesh.uv, {"front": front}, {"front": camera}, resolution=128
    )
    # One view cannot see the whole body, and the gap must be admitted.
    assert texture.covered_fraction() < 1.0
    assert texture.coverage.any()


def test_more_views_cover_more_of_the_body(cage) -> None:
    params, body_cage = cage
    mesh = cage_to_mesh(body_cage, subdivisions=0, with_uv=True)
    views, cameras = {}, {}
    for view, tint in (("front", (200, 60, 60)), ("side", (60, 60, 200)), ("back", (60, 200, 60))):
        views[view], cameras[view] = photo(mesh, view, tint)

    one = project_views_to_texture(
        mesh, mesh.uv, {"front": views["front"]}, {"front": cameras["front"]}, resolution=128
    )
    three = project_views_to_texture(mesh, mesh.uv, views, cameras, resolution=128)
    assert three.covered_fraction() > one.covered_fraction()


def test_a_mismatched_uv_count_is_rejected(cage) -> None:
    params, body_cage = cage
    mesh = cage_to_mesh(body_cage, subdivisions=0, with_uv=True)
    front, camera = photo(mesh, "front", (200, 60, 60))
    with pytest.raises(ValueError):
        project_views_to_texture(
            mesh, np.zeros((5, 2), np.float32), {"front": front}, {"front": camera}
        )


def test_texturing_with_no_views_is_rejected(cage) -> None:
    params, body_cage = cage
    mesh = cage_to_mesh(body_cage, subdivisions=0, with_uv=True)
    with pytest.raises(ValueError):
        project_views_to_texture(mesh, mesh.uv, {}, {})


def test_cameras_are_built_only_for_known_views() -> None:
    views = {
        "front": np.zeros((100, 60, 3), np.uint8),
        "selfie": np.zeros((100, 60, 3), np.uint8),
    }
    assert set(cameras_for_views(views, 180.0)) == {"front"}
