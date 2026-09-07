"""Convert reviewed MPFB CC0 rig data into the Sveyra canonical rig schema."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sveyra_human.canonical.obj import load_obj
from sveyra_human.canonical.rig_import import convert_mpfb_rig


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--body", type=Path, required=True, help="reviewed upstream base OBJ")
    parser.add_argument("--rig", type=Path, required=True, help="reviewed upstream rig JSON")
    parser.add_argument(
        "--weights", type=Path, required=True, help="reviewed upstream weights JSON"
    )
    parser.add_argument("--group", default="body", help="OBJ group retained by the canonical mesh")
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args()

    raw_rig = json.loads(arguments.rig.read_text(encoding="utf-8"))
    raw_weights = json.loads(arguments.weights.read_text(encoding="utf-8"))
    converted = convert_mpfb_rig(
        raw_rig,
        raw_weights,
        load_obj(arguments.body),
        arguments.group,
    )

    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    arguments.out.write_text(
        json.dumps(converted, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(converted["conversion_statistics"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
