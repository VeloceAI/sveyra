import numpy as np
import pytest

from sveyra_human.body.parameters import BodyParameters
from sveyra_human.canonical import deform_canonical_human, load_canonical_body, load_canonical_rig


def test_neutral_parameters_preserve_scaled_canonical_rest_state() -> None:
    height = 178.0
    body, rig, report = deform_canonical_human(BodyParameters(height=height))

    assert np.allclose(body.vertices_cm, load_canonical_body().scaled_to_height(height).vertices_cm)
    assert np.allclose(
        rig.head_positions_cm,
        load_canonical_rig().scaled_to_height(height).head_positions_cm,
    )
    assert not report.parameter_fitted
    assert report.clamped_fields == ()


def test_measurement_fit_preserves_topology_uvs_and_skin_weights() -> None:
    source_body = load_canonical_body()
    source_rig = load_canonical_rig()
    params = BodyParameters(
        height=180.0,
        shoulder_width=50.0,
        chest_width=42.0,
        chest_depth=25.0,
        waist_width=36.0,
        waist_depth=24.0,
        hip_width=42.0,
        hip_depth=27.0,
        thigh_width=20.0,
        calf_width=14.0,
        head_width=17.5,
    )

    body, rig, report = deform_canonical_human(params, source_body, source_rig)

    assert body.vertex_count == source_body.vertex_count
    assert body.polygons is source_body.polygons
    assert body.texture_coordinates is source_body.texture_coordinates
    assert body.polygon_texture_indices is source_body.polygon_texture_indices
    assert rig.joint_count == source_rig.joint_count
    assert rig.joint_indices is source_rig.joint_indices
    assert rig.weights is source_rig.weights
    assert body.height_cm == pytest.approx(180.0, abs=0.001)
    assert np.isfinite(body.vertices_cm).all()
    assert report.parameter_fitted


def test_waist_width_change_is_local_and_moves_waist_outward() -> None:
    height = 180.0
    neutral, _, _ = deform_canonical_human(BodyParameters(height=height))
    wider, _, _ = deform_canonical_human(BodyParameters(height=height, waist_width=40.0))
    vertices = neutral.vertices_cm

    waist = np.abs(vertices[:, 1] - 0.62 * height) < 2.0
    central = waist & (np.abs(vertices[:, 0]) < 20.0)
    crown = vertices[:, 1] > 0.96 * height
    assert np.max(np.abs(wider.vertices_cm[central, 0])) > np.max(
        np.abs(neutral.vertices_cm[central, 0])
    ) * 1.15
    assert np.allclose(wider.vertices_cm[crown], neutral.vertices_cm[crown], atol=1e-4)


def test_arm_and_leg_dimensions_use_semantic_skin_regions() -> None:
    height = 180.0
    neutral, neutral_rig, _ = deform_canonical_human(BodyParameters(height=height))
    shaped, shaped_rig, _ = deform_canonical_human(
        BodyParameters(
            height=height,
            upper_arm_radius=8.0,
            forearm_radius=5.5,
            thigh_width=24.0,
            thigh_depth=23.0,
            calf_width=17.0,
            calf_depth=17.0,
        )
    )

    names = np.asarray([bone.name for bone in neutral_rig.bones], dtype=str)
    upperarm_indices = np.flatnonzero(np.char.startswith(names, "upperarm"))
    upperarm_weight = np.sum(
        np.where(
            np.isin(neutral_rig.joint_indices, upperarm_indices),
            neutral_rig.weights,
            0.0,
        ),
        axis=1,
    )
    leg_indices = np.flatnonzero(
        np.char.startswith(names, "upperleg") | np.char.startswith(names, "lowerleg")
    )
    leg_weight = np.sum(
        np.where(np.isin(neutral_rig.joint_indices, leg_indices), neutral_rig.weights, 0.0),
        axis=1,
    )

    arm_shift = np.linalg.norm(
        shaped.vertices_cm[upperarm_weight > 0.8] - neutral.vertices_cm[upperarm_weight > 0.8],
        axis=1,
    )
    leg_shift = np.linalg.norm(
        shaped.vertices_cm[leg_weight > 0.8] - neutral.vertices_cm[leg_weight > 0.8],
        axis=1,
    )
    assert np.mean(arm_shift) > 1.0
    assert np.mean(leg_shift) > 1.0
    assert not np.allclose(shaped_rig.head_positions_cm, neutral_rig.head_positions_cm)


def test_extreme_ratios_are_reported_and_bounded() -> None:
    _, _, report = deform_canonical_human(
        BodyParameters(height=180.0, waist_width=100.0)
    )

    assert report.requested_ratios["waist_width"] > report.applied_ratios["waist_width"]
    assert report.applied_ratios["waist_width"] == pytest.approx(1.6)
    assert report.clamped_fields == ("waist_width",)


def test_safe_extreme_fit_keeps_every_triangle_non_degenerate_and_oriented() -> None:
    neutral, _, _ = deform_canonical_human(BodyParameters(height=180.0))
    shaped, _, _ = deform_canonical_human(
        BodyParameters(
            height=180.0,
            shoulder_width=55.0,
            chest_width=48.0,
            chest_depth=30.0,
            waist_width=42.0,
            waist_depth=30.0,
            hip_width=48.0,
            hip_depth=32.0,
            upper_arm_radius=8.0,
            forearm_radius=6.0,
            thigh_width=25.0,
            thigh_depth=25.0,
            calf_width=18.0,
            calf_depth=18.0,
            head_width=19.0,
            head_depth=24.0,
        )
    )
    faces = neutral.to_surface_mesh(with_uv=False).faces
    before, after = neutral.vertices_cm[faces], shaped.vertices_cm[faces]
    before_normals = np.cross(before[:, 1] - before[:, 0], before[:, 2] - before[:, 0])
    after_normals = np.cross(after[:, 1] - after[:, 0], after[:, 2] - after[:, 0])

    assert np.all(np.linalg.norm(after_normals, axis=1) > 1e-7)
    assert np.all(np.sum(before_normals * after_normals, axis=1) > 0)


@pytest.mark.parametrize("value", [0.0, -1.0, float("nan"), float("inf")])
def test_invalid_cross_section_measurement_is_rejected(value: float) -> None:
    with pytest.raises(ValueError, match="waist_width"):
        deform_canonical_human(BodyParameters(height=180.0, waist_width=value))
