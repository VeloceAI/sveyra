from io import StringIO
from pathlib import Path

import numpy as np
import pytest

from sveyra_human.api.engine import SveyraHumanEngine
from sveyra_human.canonical.body import load_canonical_body
from sveyra_human.canonical.obj import ObjParseError, _load_obj_stream, load_obj, write_obj_group
from sveyra_human.canonical.topology import (
    CanonicalMeshPolicy,
    analyze_topology,
    canonical_mesh_issues,
)

TETRAHEDRON = """\
v 0 0 0
v 1 0 0
v 0 1 0
v 0 0 1
vt 0 0
vt 1 0
vt 0 1
vt 1 1
g body
f 1/1 3/3 2/2
f 1/1 2/2 4/4
f 2/2 3/3 4/4
f 3/3 1/1 4/4
"""


def load_text(value: str):
    return _load_obj_stream(StringIO(value))


def permissive_policy(**changes: object) -> CanonicalMeshPolicy:
    values = {
        "minimum_vertices": 1,
        "maximum_vertices": 100,
        "require_single_component": True,
        "require_watertight": True,
        "require_consistent_winding": True,
        "require_complete_uvs": True,
        "allowed_polygon_sizes": (3, 4),
    }
    values.update(changes)
    return CanonicalMeshPolicy(**values)  # type: ignore[arg-type]


def test_closed_tetrahedron_passes_topology_policy() -> None:
    report = analyze_topology(load_text(TETRAHEDRON), "body")

    assert report.is_watertight
    assert report.has_complete_uvs
    assert report.component_count == 1
    assert report.triangle_count == 4
    assert report.extents == (1.0, 1.0, 1.0)
    assert canonical_mesh_issues(report, permissive_policy()) == []


def test_group_selection_excludes_other_geometry() -> None:
    document = load_text(
        TETRAHEDRON
        + """\
g helper
v 10 10 10
v 11 10 10
v 10 11 10
f 5/1 6/2 7/3
"""
    )

    body = analyze_topology(document, "body")
    whole = analyze_topology(document)

    assert body.referenced_vertex_count == 4
    assert body.component_count == 1
    assert whole.referenced_vertex_count == 7
    assert whole.component_count == 2


def test_open_surface_reports_boundary_edges_and_missing_uvs() -> None:
    report = analyze_topology(
        load_text("v 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\nf 1 2 3 4\n")
    )

    assert report.boundary_edge_count == 4
    assert not report.is_watertight
    issues = canonical_mesh_issues(report, permissive_policy())
    assert any("watertight" in issue for issue in issues)
    assert any("UV" in issue for issue in issues)


def test_negative_indices_are_resolved_at_the_face() -> None:
    document = load_text("v 0 0 0\nv 1 0 0\nv 0 1 0\nf -3 -2 -1\n")
    assert document.faces[0].vertex_indices == (0, 1, 2)


@pytest.mark.parametrize(
    "face",
    ["f 0 2 3", "f 1 2 99", "f 1/0 2/1 3/1", "f 1 2"],
)
def test_invalid_faces_are_rejected(face: str) -> None:
    source = f"v 0 0 0\nv 1 0 0\nv 0 1 0\nvt 0 0\n{face}\n"
    with pytest.raises(ObjParseError):
        load_text(source)


@pytest.mark.parametrize("record", ["v nan 0 0", "vt inf 0", "vn 0 -inf 0"])
def test_non_finite_geometry_is_rejected(record: str) -> None:
    with pytest.raises(ObjParseError, match="finite"):
        load_text(record + "\n")


def test_same_direction_shared_edge_is_detected() -> None:
    document = load_text(
        "v 0 0 0\nv 1 0 0\nv 0 1 0\nv 1 1 0\nf 1 2 3\nf 1 2 4\n"
    )
    assert analyze_topology(document).inconsistent_winding_edge_count == 1


def test_group_export_remaps_indices_and_preserves_topology(tmp_path: Path) -> None:
    source = load_text(
        TETRAHEDRON
        + "v 9 9 9\ng helper\nv 10 10 10\nv 11 10 10\nv 10 11 10\nf 6/1 7/2 8/3\n"
    )
    destination = tmp_path / "body.obj"

    write_obj_group(source, destination, "body", comments=("test derivative",))
    exported = load_obj(destination)

    assert len(exported.vertices) == 4
    assert len(exported.faces) == 4
    assert exported.groups == ("body",)
    assert analyze_topology(exported).is_watertight
    assert destination.read_text(encoding="utf-8").startswith("# test derivative\n")


def test_bundled_body_is_hash_pinned_and_metric() -> None:
    body = load_canonical_body()

    assert body.topology_id == "sveyra-hm08-body"
    assert body.vertex_count == 13_380
    assert body.polygon_count == 13_378
    assert body.triangle_count == 26_756
    assert body.height_cm == pytest.approx(166.589, abs=0.001)


def test_body_scales_to_height_without_changing_topology() -> None:
    body = load_canonical_body()
    short = body.scaled_to_height(155.0)
    tall = body.scaled_to_height(205.0)

    assert short.height_cm == pytest.approx(155.0, abs=0.001)
    assert tall.height_cm == pytest.approx(205.0, abs=0.001)
    assert float(short.vertices_cm[:, 1].min()) == pytest.approx(0.0)
    assert short.polygons is body.polygons
    assert tall.polygons is body.polygons


def test_body_builds_render_mesh_with_uv_seams_and_stable_faces() -> None:
    body = load_canonical_body().scaled_to_height(180.0)
    geometric = body.to_surface_mesh(with_uv=False)
    textured = body.to_surface_mesh(with_uv=True)

    assert geometric.vertex_count == 13_380
    assert geometric.face_count == 26_756
    assert textured.vertex_count >= geometric.vertex_count
    assert textured.face_count == geometric.face_count
    assert textured.uv is not None
    assert textured.uv.shape == (textured.vertex_count, 2)
    assert np.isfinite(textured.vertices).all()
    assert np.isfinite(textured.uv).all()


def test_engine_exposes_metric_canonical_seed() -> None:
    mesh = SveyraHumanEngine().build_canonical_seed(184.0, with_uv=False)
    minimum, maximum = mesh.bounds()

    assert float(maximum[1] - minimum[1]) == pytest.approx(184.0, abs=0.001)
    assert mesh.vertex_count == 13_380
