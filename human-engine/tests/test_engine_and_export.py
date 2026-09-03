"""End-to-end: engine, export, providers, and the parameter-recovery harness."""

import json
import struct
from pathlib import Path

import numpy as np
import pytest

from sveyra_human import BodyParameters, NotImplementedYetError, SveyraHumanEngine
from sveyra_human.api.models import AvatarBuildRequest
from sveyra_human.providers.mock.tryon import MockTryOnProvider
from sveyra_human.providers.vertex.tryon import VertexTryOnProvider
from sveyra_human.quality.confidence import parametric_report


@pytest.fixture
def engine() -> SveyraHumanEngine:
    return SveyraHumanEngine(quality_mode="draft")


# -- build ---------------------------------------------------------------


def test_build_parametric_produces_a_mesh(engine: SveyraHumanEngine) -> None:
    artifact = engine.build_parametric(BodyParameters(height=184.0))
    assert artifact._mesh.vertex_count > 0
    assert artifact.measurements["height_cm"] == 184.0
    assert artifact.profiling_ms["total_ms"] > 0


def test_crown_sits_at_the_requested_height(engine: SveyraHumanEngine) -> None:
    for height in (150.0, 180.0, 205.0):
        artifact = engine.build_parametric(BodyParameters(height=height))
        _, high = artifact._mesh.bounds()
        assert float(high[1]) == pytest.approx(height, abs=0.01)


def test_the_body_stands_on_the_floor(engine: SveyraHumanEngine) -> None:
    low, _ = engine.build_parametric(BodyParameters(height=180.0))._mesh.bounds()
    assert 0.0 <= float(low[1]) <= 0.5


def test_the_same_parameters_always_give_the_same_body(engine: SveyraHumanEngine) -> None:
    a = engine.build_parametric(BodyParameters(height=175.0, waist_width=32.0))
    b = engine.build_parametric(BodyParameters(height=175.0, waist_width=32.0))
    assert np.array_equal(a._mesh.vertices, b._mesh.vertices)


@pytest.mark.parametrize(
    ("field", "value", "measurement"),
    [
        ("waist_width", 45.0, "waist_girth_cm"),
        ("hip_width", 48.0, "hip_girth_cm"),
        ("chest_depth", 30.0, "chest_girth_cm"),
    ],
)
def test_changing_a_parameter_changes_its_measurement(
    engine: SveyraHumanEngine, field: str, value: float, measurement: str
) -> None:
    base = engine.build_parametric(BodyParameters(height=180.0))
    changed = engine.build_parametric(BodyParameters(height=180.0, **{field: value}))
    assert changed.measurements[measurement] > base.measurements[measurement] * 1.1


def test_higher_quality_means_a_denser_mesh() -> None:
    params = BodyParameters(height=180.0)
    draft = SveyraHumanEngine("draft").build_parametric(params)
    high = SveyraHumanEngine("high").build_parametric(params)
    assert high._mesh.face_count > draft._mesh.face_count


# -- honesty about what is not built yet ---------------------------------


def test_photo_build_refuses_rather_than_faking_success(engine: SveyraHumanEngine) -> None:
    with pytest.raises(NotImplementedYetError):
        engine.build(front="a.jpg", side="b.jpg", height_cm=180)


@pytest.mark.parametrize("stage", ["fit_face", "generate_texture", "build_hair"])
def test_unbuilt_stages_say_so(engine: SveyraHumanEngine, stage: str) -> None:
    with pytest.raises(NotImplementedYetError):
        getattr(engine, stage)()


def test_a_parametric_build_never_claims_photographic_confidence(
    engine: SveyraHumanEngine,
) -> None:
    artifact = engine.build_parametric(BodyParameters(height=180.0))
    assert artifact.source_views == 0
    assert artifact.quality.warnings


def test_confidence_rises_with_the_number_of_supplied_measurements() -> None:
    sparse = parametric_report(1, 20)
    rich = parametric_report(18, 20)
    assert rich.overall > sparse.overall
    assert any("generic" in w for w in sparse.warnings)


# -- request contract ----------------------------------------------------


def test_request_counts_supplied_views() -> None:
    request = AvatarBuildRequest(height_cm=180.0, front_image="f.jpg", side_image="s.jpg")
    assert request.supplied_views == 2


@pytest.mark.parametrize(
    "kwargs",
    [
        {"height_cm": 0.0},
        {"height_cm": 180.0, "quality_mode": "ultra"},
        {"height_cm": 180.0, "texture_resolution": 999},
    ],
)
def test_request_rejects_bad_input(kwargs: dict) -> None:
    with pytest.raises(ValueError):
        AvatarBuildRequest(**kwargs)


# -- export --------------------------------------------------------------


def test_export_writes_a_valid_glb_and_sidecars(
    engine: SveyraHumanEngine, tmp_path: Path
) -> None:
    artifact = engine.build_parametric(BodyParameters(height=184.0))
    target = artifact.export(tmp_path / "person.glb")

    assert target.exists() and target.stat().st_size > 1000
    with target.open("rb") as handle:
        magic, version, length = struct.unpack("<III", handle.read(12))
    assert magic == 0x46546C67
    assert version == 2
    assert length == target.stat().st_size

    for name in ("body_parameters.json", "measurements.json", "skeleton.json", "quality.json"):
        assert (tmp_path / name).exists(), name

    metadata = json.loads((tmp_path / "metadata.json").read_text())
    assert metadata["height_cm"] == 184.0
    assert metadata["version"] == "0.1"


def test_an_avatar_is_reproducible_from_its_json_alone(
    engine: SveyraHumanEngine, tmp_path: Path
) -> None:
    """The identity is the parameters, so the photographs must not be needed twice."""
    original = engine.build_parametric(BodyParameters(height=173.0, hip_width=40.0))
    original.export(tmp_path / "a.glb")

    stored = json.loads((tmp_path / "body_parameters.json").read_text())
    rebuilt = engine.build_parametric(BodyParameters.from_dict(stored))

    assert np.array_equal(original._mesh.vertices, rebuilt._mesh.vertices)


def test_export_is_in_metres_not_centimetres(
    engine: SveyraHumanEngine, tmp_path: Path
) -> None:
    """glTF is metre-based; a 1.8 m human must not arrive 180 m tall."""
    import pygltflib

    artifact = engine.build_parametric(BodyParameters(height=180.0))
    artifact.export(tmp_path / "person.glb")
    gltf = pygltflib.GLTF2().load(str(tmp_path / "person.glb"))
    assert gltf.accessors[0].max[1] == pytest.approx(1.80, abs=0.01)


# -- provider seam -------------------------------------------------------


def test_mock_provider_is_deterministic() -> None:
    provider = MockTryOnProvider()
    assert provider.generate("p", "g") == provider.generate("p", "g")
    assert provider.name == "mock"


def test_vertex_provider_is_declared_but_not_built() -> None:
    with pytest.raises(NotImplementedYetError):
        VertexTryOnProvider().generate("p", "g")


def test_the_core_engine_never_imports_a_provider() -> None:
    """Vendor neutrality is a structural property, so assert it structurally."""
    root = Path(__file__).resolve().parents[1] / "src" / "sveyra_human"
    core = ["api", "body", "skeleton", "export", "camera", "optimization"]
    for area in core:
        for path in (root / area).rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            assert "providers.vertex" not in source, path
            assert "google.cloud" not in source, path
