"""Command line entry point.

    sveyra build-parametric --height 184 --shoulder-width 46 --out person.glb
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sveyra_human.api.engine import SveyraHumanEngine
from sveyra_human.api.models import SUBDIVISIONS
from sveyra_human.body.parameters import BodyParameters

# CLI flag -> BodyParameters field. Only the dimensions worth setting by hand;
# everything else follows from height.
_PARAM_FLAGS = {
    "shoulder-width": "shoulder_width",
    "shoulder-depth": "shoulder_depth",
    "chest-width": "chest_width",
    "chest-depth": "chest_depth",
    "waist-width": "waist_width",
    "waist-depth": "waist_depth",
    "hip-width": "hip_width",
    "hip-depth": "hip_depth",
    "neck-width": "neck_width",
    "upper-arm-length": "upper_arm_length",
    "forearm-length": "forearm_length",
    "thigh-length": "thigh_length",
    "thigh-width": "thigh_width",
    "calf-length": "calf_length",
    "calf-width": "calf_width",
}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sveyra", description="SVEYRA Human Engine")
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser(
        "build-parametric",
        help="Build a GLB human from measurements alone. No photographs.",
    )
    build.add_argument("--height", type=float, required=True, help="standing height in cm")
    for flag, field in _PARAM_FLAGS.items():
        build.add_argument(f"--{flag}", type=float, default=None, help=f"{field} in cm")
    build.add_argument("--out", type=Path, default=Path("avatar.glb"))
    build.add_argument("--quality", choices=sorted(SUBDIVISIONS), default="balanced")
    build.add_argument("--json", action="store_true", help="print metadata as JSON")

    photo = sub.add_parser(
        "build-from-photos",
        help="Build a GLB human from photographs.",
    )
    photo.add_argument("--front", type=Path, required=True)
    photo.add_argument("--side", type=Path, default=None)
    photo.add_argument("--back", type=Path, default=None)
    photo.add_argument("--height", type=float, required=True, help="standing height in cm")
    photo.add_argument("--out", type=Path, default=Path("avatar.glb"))
    photo.add_argument("--quality", choices=sorted(SUBDIVISIONS), default="balanced")
    photo.add_argument("--json", action="store_true")

    sub.add_parser("info", help="show what this build of the engine can do")
    return parser


def _run_build(args: argparse.Namespace) -> int:
    supplied = {
        field: getattr(args, flag.replace("-", "_"))
        for flag, field in _PARAM_FLAGS.items()
        if getattr(args, flag.replace("-", "_")) is not None
    }
    params = BodyParameters(height=args.height, **supplied)

    engine = SveyraHumanEngine(quality_mode=args.quality)
    artifact = engine.build_parametric(params)
    path = artifact.export(args.out)

    if args.json:
        print(artifact.to_json())
        return 0

    mesh = artifact._mesh
    print(f"wrote {path}")
    print(f"  vertices     {mesh.vertex_count:,}")  # type: ignore[union-attr]
    print(f"  triangles    {mesh.face_count:,}")  # type: ignore[union-attr]
    print(f"  supplied     {len(supplied)} of {len(_PARAM_FLAGS)} optional measurements")
    print("  measurements " + json.dumps(artifact.measurements))
    print(f"  total        {artifact.profiling_ms.get('total_ms', 0.0)} ms")
    for warning in artifact.quality.warnings:
        print(f"  note: {warning}")
    return 0


def _run_photo_build(args: argparse.Namespace) -> int:
    from sveyra_human.api.errors import SveyraHumanError

    engine = SveyraHumanEngine(quality_mode=args.quality)
    try:
        artifact = engine.build(
            front=args.front,
            side=args.side,
            back=args.back,
            height_cm=args.height,
        )
    except SveyraHumanError as error:
        print(f"could not build an avatar: {error}", file=sys.stderr)
        return 1

    path = artifact.export(args.out)
    if args.json:
        print(artifact.to_json())
        return 0

    print(f"wrote {path}")
    print(f"  views used   {artifact.source_views}")
    print(f"  confidence   {artifact.quality.overall}")
    print("  measurements " + json.dumps(artifact.measurements))
    print(f"  total        {artifact.profiling_ms.get('total_ms', 0.0)} ms")
    for warning in artifact.quality.warnings:
        print(f"  note: {warning}")
    return 0


def _run_info() -> int:
    print("SVEYRA Human Engine 0.1.0")
    print("  working:  parametric body, silhouette fitting, photo segmentation,")
    print("            skinned rig, collision proxies, GLB export")
    print("  missing:  face fitting, texturing, hair, try-on providers")
    print("  see docs/STATUS.md")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "build-parametric":
        return _run_build(args)
    if args.command == "build-from-photos":
        return _run_photo_build(args)
    return _run_info()


if __name__ == "__main__":
    sys.exit(main())
