"""SVEYRA Human Engine.

Lightweight AI finds the features, mathematics builds the body.
"""

from sveyra_human.api import (
    AvatarArtifact,
    AvatarBuildRequest,
    NotImplementedYetError,
    QualityReport,
    SveyraHumanEngine,
    SveyraHumanError,
)
from sveyra_human.body.parameters import BodyParameters
from sveyra_human.canonical import (
    CanonicalBodyMesh,
    CanonicalDeformationReport,
    CanonicalRig,
    deform_canonical_human,
    load_canonical_body,
    load_canonical_rig,
)
from sveyra_human.digital_human import (
    DigitalHumanManifest,
    is_photoreal_animation_ready,
    photoreal_animation_issues,
)

__version__ = "0.1.0"

__all__ = [
    "AvatarArtifact",
    "AvatarBuildRequest",
    "BodyParameters",
    "CanonicalBodyMesh",
    "CanonicalDeformationReport",
    "CanonicalRig",
    "DigitalHumanManifest",
    "NotImplementedYetError",
    "QualityReport",
    "SveyraHumanEngine",
    "SveyraHumanError",
    "deform_canonical_human",
    "is_photoreal_animation_ready",
    "load_canonical_body",
    "load_canonical_rig",
    "photoreal_animation_issues",
    "__version__",
]
