import json
from io import StringIO
from pathlib import Path

import numpy as np
import pygltflib
import pytest

from sveyra_human.canonical.body import load_canonical_body
from sveyra_human.canonical.obj import _load_obj_stream
from sveyra_human.canonical.rig import CanonicalRigError, load_canonical_rig
from sveyra_human.canonical.rig_import import convert_mpfb_rig
from sveyra_human.export.canonical_gltf import export_canonical_skinned_glb


def source_body():
    return _load_obj_stream(
        StringIO(
            """\
v 0 0 0
v 1 0 0
v 0 1 0
v 0 0 1
v 10 10 10
v 11 10 10
v 10 11 10
g body
f 1 3 2
f 1 2 4
f 2 3 4
f 3 1 4
g helper
f 5 6 7
"""
        )
    )


def endpoint(x: float, y: float, z: float) -> dict[str, object]:
    return {"default_position": [x, y, z], "strategy": "VERTEX"}


def source_rig() -> dict[str, object]:
    # Deliberately put children first; conversion must topologically order them.
    return {
        **{
            f"bone{number}": {
                "parent": "root",
                "head": endpoint(number / 100.0, 0.0, 0.05),
                "tail": endpoint(number / 100.0, 0.0, 0.08),
                "roll": 0.0,
            }
            for number in range(1, 5)
        },
        "root": {
            "parent": None,
            "head": endpoint(0.0, 0.0, 0.0),
            "tail": endpoint(0.0, 0.0, 0.05),
            "roll": 0.0,
        },
    }


def source_weights() -> dict[str, object]:
    return {
        "license": "CC0",
        "weights": {
            "root": [[0, 0.1], [1, 1.0], [2, 1.0], [3, 1.0], [4, 1.0]],
            "bone1": [[0, 0.9]],
            "bone2": [[0, 0.8]],
            "bone3": [[0, 0.7]],
            "bone4": [[0, 0.6]],
        },
    }


def test_conversion_filters_helpers_caps_weights_and_orders_hierarchy(tmp_path: Path) -> None:
    converted = convert_mpfb_rig(source_rig(), source_weights(), source_body())
    statistics = converted["conversion_statistics"]

    assert [bone["name"] for bone in converted["bones"]] == [
        "root",
        "bone1",
        "bone2",
        "bone3",
        "bone4",
    ]
    assert statistics["filtered_non_body_entries"] == 1
    assert statistics["dropped_body_influences_over_limit"] == 1

    target = tmp_path / "rig.json"
    target.write_text(json.dumps(converted), encoding="utf-8")
    rig = load_canonical_rig(target)

    assert rig.joint_count == 5
    assert rig.vertex_count == 4
    assert rig.root_indices == (0,)
    assert np.allclose(rig.weights.sum(axis=1), 1.0)
    assert rig.joint_indices[0].tolist() == [1, 2, 3, 4]


def test_coordinate_conversion_is_metric_y_up() -> None:
    converted = convert_mpfb_rig(source_rig(), source_weights(), source_body())
    root = converted["bones"][0]
    first_child = converted["bones"][1]

    assert converted["base_height_cm"] == 10.0
    assert root["head_cm"] == [0.0, 0.0, -0.0]
    assert first_child["head_cm"] == [1.0, 5.0, -0.0]


def test_conversion_requires_explicit_cc0_weights() -> None:
    weights = source_weights()
    weights["license"] = "unknown"
    with pytest.raises(CanonicalRigError, match="CC0"):
        convert_mpfb_rig(source_rig(), weights, source_body())


def test_conversion_rejects_hierarchy_cycles() -> None:
    rig = source_rig()
    rig["root"]["parent"] = "bone1"
    with pytest.raises(CanonicalRigError, match="cycle"):
        convert_mpfb_rig(rig, source_weights(), source_body())


def test_bundled_rig_is_hash_pinned_and_covers_every_canonical_vertex() -> None:
    rig = load_canonical_rig()

    assert rig.joint_count == 163
    assert rig.vertex_count == 13_380
    assert rig.root_indices == (0,)
    assert {"jaw", "eye.L", "eye.R", "tongue00", "finger1-1.L"}.issubset(
        bone.name for bone in rig.bones
    )
    assert np.allclose(rig.weights.sum(axis=1), 1.0)
    assert int(rig.joint_indices.max()) < rig.joint_count


def test_rig_scaling_preserves_hierarchy_and_matches_requested_height() -> None:
    rig = load_canonical_rig()
    scaled = rig.scaled_to_height(190.0)

    assert scaled.base_height_cm == pytest.approx(190.0)
    assert [bone.parent_index for bone in scaled.bones] == [
        bone.parent_index for bone in rig.bones
    ]
    assert np.allclose(
        scaled.head_positions_cm,
        rig.head_positions_cm * (190.0 / rig.base_height_cm),
    )


def test_local_joint_translations_reconstruct_world_heads() -> None:
    rig = load_canonical_rig()
    local = rig.local_translations_cm()
    reconstructed = np.zeros_like(local)

    for index, bone in enumerate(rig.bones):
        reconstructed[index] = local[index]
        if bone.parent_index is not None:
            reconstructed[index] += reconstructed[bone.parent_index]

    assert np.allclose(reconstructed, rig.head_positions_cm, atol=1e-5)


def test_canonical_export_contains_skin_and_all_joints(tmp_path: Path) -> None:
    height = 181.0
    body = load_canonical_body().scaled_to_height(height)
    rig = load_canonical_rig().scaled_to_height(height)
    target = export_canonical_skinned_glb(body, rig, tmp_path / "rigged.glb")
    gltf = pygltflib.GLTF2().load(str(target))

    assert len(gltf.skins) == 1
    assert len(gltf.skins[0].joints) == 163
    assert len(gltf.nodes) == 164
    assert gltf.nodes[0].skin == 0
    primitive = gltf.meshes[0].primitives[0]
    assert primitive.attributes.JOINTS_0 is not None
    assert primitive.attributes.WEIGHTS_0 is not None
    assert gltf.accessors[0].max[1] == pytest.approx(1.81, abs=0.001)
