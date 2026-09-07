"""Acceptance gates for the first photoreal, animatable SVEYRA human."""

from __future__ import annotations

from sveyra_human.digital_human.manifest import DigitalHumanManifest

REQUIRED_MEASUREMENTS = {"height", "chest_girth", "waist_girth", "hip_girth"}
REQUIRED_REGIONS = {"body", "face", "hands", "skin", "hair"}
REQUIRED_TEXTURE_MAPS = {"base_color", "normal", "roughness", "subsurface"}
REQUIRED_FILE_ROLES = {
    "body_mesh",
    "hair_geometry",
    "albedo_texture",
    "normal_texture",
    "roughness_texture",
    "subsurface_texture",
}
MIN_REGION_CONFIDENCE = 0.75


def photoreal_animation_issues(manifest: DigitalHumanManifest) -> list[str]:
    """Explain every reason a manifest is not ready for the first product gate."""
    issues: list[str] = []
    capture = manifest.capture
    if capture.mode not in {"multi_view_images", "guided_video", "depth_assisted"}:
        issues.append("capture must contain multiple views or guided video")
    if capture.source_views < 3:
        issues.append("capture must provide at least three body views")
    if capture.scale_source == "unknown":
        issues.append("capture needs a metric scale source")
    if not capture.body_capture or not capture.face_capture:
        issues.append("capture must include both body and close face evidence")
    if not capture.neutral_expression:
        issues.append("capture must include a neutral facial expression")

    geometry = manifest.geometry
    if not geometry.watertight:
        issues.append("body surface must be watertight")
    geometry_flags = {
        "hands": geometry.has_hands,
        "feet": geometry.has_feet,
        "eyes": geometry.has_eyes,
        "mouth cavity": geometry.has_mouth_cavity,
        "teeth": geometry.has_teeth,
        "tongue": geometry.has_tongue,
    }
    for label, present in geometry_flags.items():
        if not present:
            issues.append(f"geometry is missing {label}")

    rig = manifest.rig
    if not rig.has_finger_rig:
        issues.append("rig is missing finger controls")
    if not rig.has_eye_gaze or not rig.has_eyelids:
        issues.append("rig is missing complete eye controls")
    if not rig.has_jaw or not rig.has_tongue_rig:
        issues.append("rig is missing complete speech controls")
    if rig.facial_blendshape_count < 52:
        issues.append("rig needs at least 52 facial blendshapes")
    if not rig.corrective_shapes:
        issues.append("rig needs joint corrective shapes")

    appearance = manifest.appearance
    missing_maps = REQUIRED_TEXTURE_MAPS - set(appearance.texture_maps)
    if missing_maps:
        issues.append(f"appearance is missing texture maps: {', '.join(sorted(missing_maps))}")
    if not appearance.lighting_neutralized:
        issues.append("appearance still contains capture lighting")
    if not appearance.has_eye_material or not appearance.has_skin_subsurface:
        issues.append("appearance is missing physical eye or skin materials")
    if appearance.hair_representation not in {"cards", "strands", "neural"}:
        issues.append("hair must use cards, strands, or a validated neural representation")

    missing_files = REQUIRED_FILE_ROLES - {asset.role for asset in manifest.files}
    if missing_files:
        issues.append(f"asset files are missing: {', '.join(sorted(missing_files))}")
    missing_measurements = REQUIRED_MEASUREMENTS - set(manifest.measurements_cm)
    if missing_measurements:
        issues.append(f"measurements are missing: {', '.join(sorted(missing_measurements))}")
    missing_regions = REQUIRED_REGIONS - set(manifest.regions)
    if missing_regions:
        issues.append(f"evidence is missing regions: {', '.join(sorted(missing_regions))}")
    for name in sorted(REQUIRED_REGIONS & set(manifest.regions)):
        evidence = manifest.regions[name]
        if evidence.confidence < MIN_REGION_CONFIDENCE:
            issues.append(f"{name} confidence is below {MIN_REGION_CONFIDENCE:.2f}")
        if evidence.basis == "template":
            issues.append(f"{name} still comes from a generic template")
    return issues


def is_photoreal_animation_ready(manifest: DigitalHumanManifest) -> bool:
    return not photoreal_animation_issues(manifest)
