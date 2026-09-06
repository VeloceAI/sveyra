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

__version__ = "0.1.0"

__all__ = [
    "AvatarArtifact",
    "AvatarBuildRequest",
    "BodyParameters",
    "NotImplementedYetError",
    "QualityReport",
    "SveyraHumanEngine",
    "SveyraHumanError",
    "__version__",
]
