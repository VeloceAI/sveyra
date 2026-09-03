"""Build three bodies from measurements alone and write them out.

    python examples/build_parametric.py [output_dir]
"""

from __future__ import annotations

import sys
from pathlib import Path

from sveyra_human import BodyParameters, SveyraHumanEngine

PEOPLE = {
    "tall_slim": BodyParameters(height=193.0, waist_width=28.0, chest_width=36.0),
    "average": BodyParameters(height=175.0),
    "broad": BodyParameters(height=178.0, shoulder_width=52.0, chest_width=44.0, waist_width=40.0),
}


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "build")
    engine = SveyraHumanEngine(quality_mode="balanced")

    for name, params in PEOPLE.items():
        artifact = engine.build_parametric(params)
        target = artifact.export(out / name / f"{name}.glb")
        m = artifact.measurements
        print(
            f"{name:12} {params.height:6.1f} cm  "
            f"chest {m['chest_girth_cm']:6.1f}  "
            f"waist {m['waist_girth_cm']:6.1f}  "
            f"hip {m['hip_girth_cm']:6.1f}  "
            f"{artifact.profiling_ms['total_ms']:6.1f} ms  -> {target}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
