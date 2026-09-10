"""Canonical mesh ingestion and topology validation."""

from sveyra_human.canonical.body import (
    CANONICAL_TOPOLOGY_ID,
    CANONICAL_TOPOLOGY_VERSION,
    CanonicalAssetError,
    CanonicalBodyMesh,
    canonical_asset_path,
    load_canonical_body,
)
from sveyra_human.canonical.deformation import (
    MAX_APPLIED_RATIO,
    MIN_APPLIED_RATIO,
    SUPPORTED_FIELDS,
    CanonicalDeformationReport,
    deform_canonical_human,
)
from sveyra_human.canonical.obj import (
    ObjDocument,
    ObjFace,
    ObjParseError,
    load_obj,
    write_obj_group,
)
from sveyra_human.canonical.rig import (
    CANONICAL_RIG_ID,
    CANONICAL_RIG_VERSION,
    CanonicalBone,
    CanonicalRig,
    CanonicalRigError,
    canonical_rig_asset_path,
    load_canonical_rig,
)
from sveyra_human.canonical.topology import (
    CanonicalMeshPolicy,
    TopologyReport,
    analyze_topology,
    canonical_mesh_issues,
)

__all__ = [
    "CANONICAL_TOPOLOGY_ID",
    "CANONICAL_TOPOLOGY_VERSION",
    "CANONICAL_RIG_ID",
    "CANONICAL_RIG_VERSION",
    "CanonicalAssetError",
    "CanonicalBone",
    "CanonicalBodyMesh",
    "CanonicalDeformationReport",
    "CanonicalMeshPolicy",
    "CanonicalRig",
    "CanonicalRigError",
    "ObjDocument",
    "ObjFace",
    "ObjParseError",
    "MAX_APPLIED_RATIO",
    "MIN_APPLIED_RATIO",
    "SUPPORTED_FIELDS",
    "TopologyReport",
    "analyze_topology",
    "canonical_asset_path",
    "canonical_mesh_issues",
    "canonical_rig_asset_path",
    "deform_canonical_human",
    "load_canonical_body",
    "load_canonical_rig",
    "load_obj",
    "write_obj_group",
]
