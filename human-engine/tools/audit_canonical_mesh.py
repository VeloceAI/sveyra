"""Print a deterministic topology audit for a Wavefront OBJ candidate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sveyra_human.canonical import (
    analyze_topology,
    canonical_mesh_issues,
    load_obj,
    write_obj_group,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mesh", type=Path)
    parser.add_argument("--group", help="Analyze only faces assigned to this OBJ group")
    parser.add_argument("--extract", type=Path, help="Write the selected group as a compact OBJ")
    arguments = parser.parse_args()

    document = load_obj(arguments.mesh)
    report = analyze_topology(document, arguments.group)
    output = report.to_dict()
    output["acceptance_issues"] = canonical_mesh_issues(report)
    print(json.dumps(output, indent=2, sort_keys=True))
    if arguments.extract:
        if not arguments.group:
            parser.error("--extract requires --group")
        write_obj_group(
            document,
            arguments.extract,
            arguments.group,
            comments=(
                "Sveyra canonical body topology seed",
                f"Derived from {arguments.mesh.name}, group {arguments.group!r}",
                "Upstream asset released under CC0 1.0; see PROVENANCE.md",
            ),
        )
    return int(bool(output["acceptance_issues"]))


if __name__ == "__main__":
    raise SystemExit(main())
