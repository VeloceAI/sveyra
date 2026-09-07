"""What the pipeline actually delivers today, against the acceptance gates.

`digital_human/acceptance.py` states what a photoreal, animatable human must
satisfy, and `test_digital_human_contract.py` proves the gates fire. Nothing
described a real build, so nothing measured the distance between the two.

This builds each figure through the canonical path, fills a manifest with what
is true right now rather than what we would like to be true, and prints every
gate that is still failing. Run it after any change that claims to close one.

    python human-engine/tools/digital_human_status.py
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sveyra_human.body.anatomy import measurements  # noqa: E402
from sveyra_human.body.figures import DEFAULT_HEIGHT_CM, figure  # noqa: E402
from sveyra_human.canonical.body import (  # noqa: E402
    CANONICAL_TOPOLOGY_ID,
    CANONICAL_TOPOLOGY_VERSION,
)
from sveyra_human.canonical.deformation import deform_canonical_human  # noqa: E402
from sveyra_human.digital_human.acceptance import photoreal_animation_issues  # noqa: E402
from sveyra_human.digital_human.manifest import (  # noqa: E402
    AppearanceManifest,
    CaptureEvidence,
    DigitalHumanManifest,
    GeometryManifest,
    RegionEvidence,
    RigManifest,
)


def _bones_matching(rig, *fragments: str) -> list[str]:
    return [b.name for b in rig.bones if any(f in b.name.lower() for f in fragments)]


def describe(kind: str) -> tuple[DigitalHumanManifest, dict[str, float]]:
    """A manifest of what one figure is today. Optimism here would be a lie."""
    params = figure(kind)
    girths = measurements(params)
    body, rig, _ = deform_canonical_human(params)

    fingers = _bones_matching(rig, "finger", "thumb", "index", "middle", "ring", "pinky")
    eyes = _bones_matching(rig, "eye")
    eyelids = [n for n in eyes if "lid" in n.lower()]

    geometry = GeometryManifest(
        topology_id=CANONICAL_TOPOLOGY_ID,
        topology_version=CANONICAL_TOPOLOGY_VERSION,
        vertex_count=body.vertex_count,
        triangle_count=body.triangle_count,
        watertight=True,
        has_hands=bool(fingers),
        has_feet=bool(_bones_matching(rig, "toe", "foot")),
        has_eyes=bool(eyes),
        # The base mesh is a closed skin. Nothing has modelled the inside of a
        # mouth, so these stay false until geometry exists rather than being
        # assumed from the presence of a jaw bone.
        has_mouth_cavity=False,
        has_teeth=False,
        has_tongue=False,
    )

    rig_manifest = RigManifest(
        skeleton_id=rig.topology_id,
        joint_count=len(rig.bones),
        facial_blendshape_standard="none",
        facial_blendshape_count=0,
        has_finger_rig=len(fingers) >= 30,
        has_eye_gaze=bool(eyes),
        has_eyelids=bool(eyelids),
        has_jaw=bool(_bones_matching(rig, "jaw")),
        has_tongue_rig=bool(_bones_matching(rig, "tongue")),
        corrective_shapes=(),
    )

    # Capture is where the pipeline is thinnest: one front photograph, scaled by
    # a height the user types in.
    capture = CaptureEvidence(
        mode="single_image",
        source_views=1,
        scale_source="user_height",
        consent_reference="none",
        body_capture=True,
        face_capture=False,
        neutral_expression=False,
    )

    appearance = AppearanceManifest(
        # The manifest will not accept a resolution of zero, so this states the
        # size a texture would be if one existed. None does; the empty map list
        # and the template skin evidence below are what say so.
        texture_resolution=1024,
        texture_maps=(),
        hair_representation="none",
        lighting_neutralized=False,
        has_eye_material=False,
        has_skin_subsurface=False,
    )

    # Only the body comes from the photograph, and only three torso girths of it.
    regions = {
        "body": RegionEvidence(basis="measured", confidence=0.7),
        "face": RegionEvidence(basis="template", confidence=0.0),
        "hands": RegionEvidence(basis="template", confidence=0.0),
        "skin": RegionEvidence(basis="template", confidence=0.0),
        "hair": RegionEvidence(basis="template", confidence=0.0),
    }

    manifest = DigitalHumanManifest(
        asset_id=f"figure:{kind}",
        capture=capture,
        geometry=geometry,
        rig=rig_manifest,
        appearance=appearance,
        regions=regions,
        measurements_cm={
            "height": float(params.height),
            "chest_girth": girths["chest_girth_cm"],
            "waist_girth": girths["waist_girth_cm"],
            "hip_girth": girths["hip_girth_cm"],
        },
        files=(),
    )
    lo = body.vertices_cm.min(axis=0)
    hi = body.vertices_cm.max(axis=0)
    size = {
        "height": float(hi[1] - lo[1]),
        "width": float(hi[0] - lo[0]),
        "depth": float(hi[2] - lo[2]),
    }
    return manifest, size


def main() -> int:
    print("Canonical figures built through deform_canonical_human:\n")
    issues: list[str] = []
    for kind in ("man", "woman", "child"):
        manifest, size = describe(kind)
        print(
            f"  {kind:<6} {DEFAULT_HEIGHT_CM[kind]:5.0f} cm target   "
            f"{manifest.geometry.vertex_count} verts  "
            f"{manifest.rig.joint_count} bones   "
            f"built {size['height']:.0f} x {size['width']:.0f} x {size['depth']:.0f} cm"
        )
        issues = photoreal_animation_issues(manifest)

    print(f"\nAcceptance gates still failing: {len(issues)}\n")
    for issue in issues:
        print(f"  - {issue}")
    print(
        "\nThe figures differ only in proportion; the gates below are the same for\n"
        "all three, so they are listed once."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
