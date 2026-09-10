"""The digital-human target is executable rather than only a visual promise."""

import json

import pytest

from sveyra_human.digital_human import (
    AppearanceManifest,
    AssetFile,
    CaptureEvidence,
    DigitalHumanManifest,
    GeometryManifest,
    ProvenanceRecord,
    RegionEvidence,
    RigManifest,
    is_photoreal_animation_ready,
    photoreal_animation_issues,
)


def complete_manifest() -> DigitalHumanManifest:
    files = (
        AssetFile("body_mesh", "humans/person-1/body.glb", "model/gltf-binary"),
        AssetFile("hair_geometry", "humans/person-1/hair.glb", "model/gltf-binary"),
        AssetFile("albedo_texture", "humans/person-1/albedo.ktx2", "image/ktx2"),
        AssetFile("normal_texture", "humans/person-1/normal.ktx2", "image/ktx2"),
        AssetFile("roughness_texture", "humans/person-1/roughness.ktx2", "image/ktx2"),
        AssetFile("subsurface_texture", "humans/person-1/subsurface.ktx2", "image/ktx2"),
    )
    regions = {
        name: RegionEvidence("observed", 0.9)
        for name in ("body", "face", "hands", "skin", "hair")
    }
    return DigitalHumanManifest(
        asset_id="person-1-v1",
        capture=CaptureEvidence(
            mode="guided_video",
            source_views=24,
            scale_source="reported_height",
            consent_reference="consents/person-1/v1",
            face_capture=True,
            neutral_expression=True,
        ),
        geometry=GeometryManifest(
            topology_id="sveyra-human",
            topology_version="1.0",
            vertex_count=50_000,
            triangle_count=98_000,
            lod_count=3,
            watertight=True,
            has_hands=True,
            has_feet=True,
            has_eyes=True,
            has_mouth_cavity=True,
            has_teeth=True,
            has_tongue=True,
        ),
        rig=RigManifest(
            skeleton_id="sveyra-humanoid-v1",
            joint_count=96,
            facial_blendshape_standard="arkit-52",
            facial_blendshape_count=52,
            has_finger_rig=True,
            has_eye_gaze=True,
            has_eyelids=True,
            has_jaw=True,
            has_tongue_rig=True,
            corrective_shapes=("shoulder_L", "shoulder_R", "hip_L", "hip_R"),
        ),
        appearance=AppearanceManifest(
            texture_resolution=4096,
            texture_maps=("base_color", "normal", "roughness", "subsurface"),
            hair_representation="cards",
            lighting_neutralized=True,
            has_eye_material=True,
            has_skin_subsurface=True,
        ),
        files=files,
        measurements_cm={
            "height": 178.0,
            "chest_girth": 98.0,
            "waist_girth": 82.0,
            "hip_girth": 96.0,
        },
        regions=regions,
        provenance=(
            ProvenanceRecord(
                component="digital human manifest",
                kind="original",
                origin="SVEYRA",
                license_id="Proprietary",
            ),
        ),
    )


def test_complete_manifest_passes_the_first_product_gate() -> None:
    manifest = complete_manifest()
    assert photoreal_animation_issues(manifest) == []
    assert is_photoreal_animation_ready(manifest)


def test_manifest_round_trips_through_json() -> None:
    manifest = complete_manifest()
    restored = DigitalHumanManifest.from_dict(json.loads(manifest.to_json()))
    assert restored.to_dict() == manifest.to_dict()


def test_manifest_refuses_an_unknown_schema_version() -> None:
    payload = complete_manifest().to_dict()
    payload["schema_version"] = "99.0"
    with pytest.raises(ValueError, match="unsupported digital-human schema"):
        DigitalHumanManifest.from_dict(payload)


def test_asset_references_are_provider_neutral() -> None:
    with pytest.raises(ValueError, match="opaque"):
        AssetFile("body_mesh", "https://bucket.example/body.glb", "model/gltf-binary")


def test_copied_material_requires_file_level_provenance() -> None:
    with pytest.raises(ValueError, match="source_path"):
        ProvenanceRecord(
            component="base mesh",
            kind="asset",
            origin="reference repository",
            license_id="CC0-1.0",
            copied=True,
        )


def test_a_current_coarse_avatar_cannot_claim_photoreal_readiness() -> None:
    manifest = complete_manifest()
    coarse = DigitalHumanManifest(
        asset_id=manifest.asset_id,
        capture=CaptureEvidence(
            mode="single_image",
            source_views=1,
            scale_source="reported_height",
            consent_reference="consents/person-1/v1",
        ),
        geometry=GeometryManifest(
            topology_id="sveyra-procedural",
            topology_version="0.1",
            vertex_count=3_528,
            triangle_count=6_768,
        ),
        rig=RigManifest(skeleton_id="sveyra-18", joint_count=18),
        appearance=AppearanceManifest(
            texture_resolution=1024,
            texture_maps=("base_color",),
            hair_representation="shell",
        ),
        files=(AssetFile("body_mesh", "humans/person-1/coarse.glb", "model/gltf-binary"),),
        measurements_cm={"height": 178.0},
        regions={"body": RegionEvidence("inferred", 0.55)},
    )
    issues = photoreal_animation_issues(coarse)
    assert "capture must contain multiple views or guided video" in issues
    assert "body surface must be watertight" in issues
    assert "rig needs at least 52 facial blendshapes" in issues
    assert not is_photoreal_animation_ready(coarse)
