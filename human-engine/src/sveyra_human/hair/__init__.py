"""Hair as grouped volumes rather than strands.

A hairstyle is a set of shells over the skull. Replacing one does not touch the
head, face or body, so identity survives a haircut.
"""

from sveyra_human.hair.groups import (
    GROUP_REGIONS,
    HairGroup,
    HairStrandChain,
    Hairstyle,
    HairVolume,
    groups_present,
)
from sveyra_human.hair.reconstruction import build_hairstyle, measure_thickness
from sveyra_human.hair.segmentation import HairMask, segment_hair

__all__ = [
    "GROUP_REGIONS",
    "HairGroup",
    "HairMask",
    "HairStrandChain",
    "HairVolume",
    "Hairstyle",
    "build_hairstyle",
    "groups_present",
    "measure_thickness",
    "segment_hair",
]
