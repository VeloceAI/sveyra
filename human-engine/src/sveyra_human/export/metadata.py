"""JSON sidecars written next to the GLB.

Everything needed to rebuild the avatar without the original photographs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sveyra_human.api.models import AvatarArtifact


def write_sidecars(artifact: AvatarArtifact, directory: str | Path) -> dict[str, Path]:
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=True)

    payloads = {
        "body_parameters.json": artifact.body_parameters.to_dict(),
        "measurements.json": artifact.measurements,
        "skeleton.json": artifact.skeleton,
        "quality.json": artifact.quality.to_dict(),
        "metadata.json": artifact.metadata(),
    }

    written: dict[str, Path] = {}
    for name, payload in payloads.items():
        path = target / name
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        written[name] = path
    return written
