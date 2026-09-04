"""Hair as a handful of volumes, not as strands.

Simulating individual strands is the wrong shape of problem for a try-on
product: it is expensive, hard to art-direct, and no one is inspecting a
hairline while deciding whether a jacket fits. Instead hair is a few named
groups, each a shell over the skull, textured from the photograph.

The payoff is swappability. A hairstyle is a set of groups; replacing it does
not touch the head, the face or the body, so identity survives a haircut.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import numpy as np


class HairGroup(str, Enum):
    FRINGE = "fringe"
    TOP = "top"
    LEFT = "left"
    RIGHT = "right"
    BACK = "back"
    SIDEBURN_LEFT = "sideburn_left"
    SIDEBURN_RIGHT = "sideburn_right"


# Where each group sits on the skull, as (azimuth range in degrees, height
# range as a fraction of head height). Azimuth 0 faces forward.
GROUP_REGIONS: dict[HairGroup, tuple[tuple[float, float], tuple[float, float]]] = {
    HairGroup.FRINGE: ((-45.0, 45.0), (0.62, 0.92)),
    # Spans three head levels, not one: a narrower band selects too few rings
    # to form a shell and the crown silently comes out bald.
    HairGroup.TOP: ((-180.0, 180.0), (0.78, 1.0)),
    HairGroup.LEFT: ((45.0, 135.0), (0.45, 0.92)),
    HairGroup.RIGHT: ((-135.0, -45.0), (0.45, 0.92)),
    HairGroup.BACK: ((135.0, 225.0), (0.40, 0.92)),
    HairGroup.SIDEBURN_LEFT: ((55.0, 95.0), (0.28, 0.48)),
    HairGroup.SIDEBURN_RIGHT: ((-95.0, -55.0), (0.28, 0.48)),
}


@dataclass
class HairStrandChain:
    """A short control chain for one lock, root to tip.

    Not simulated here. It exists so a downstream solver can attach springs
    without re-deriving where the hair is anchored.
    """

    root: np.ndarray
    nodes: np.ndarray  # (n, 3)

    @property
    def length(self) -> float:
        if self.nodes.shape[0] < 2:
            return 0.0
        return float(np.linalg.norm(np.diff(self.nodes, axis=0), axis=1).sum())


@dataclass
class HairVolume:
    """One group as a shell of rings offset from the skull."""

    group: HairGroup
    rings: np.ndarray  # (levels, segments, 3)
    thickness_cm: float
    chains: list[HairStrandChain] = field(default_factory=list)

    @property
    def vertex_count(self) -> int:
        return int(self.rings.shape[0] * self.rings.shape[1])


@dataclass
class Hairstyle:
    """A complete head of hair, swappable as a unit."""

    volumes: list[HairVolume] = field(default_factory=list)
    source: str = "reconstructed"

    def group(self, group: HairGroup) -> HairVolume:
        for volume in self.volumes:
            if volume.group is group:
                return volume
        raise KeyError(group)

    @property
    def vertex_count(self) -> int:
        return sum(v.vertex_count for v in self.volumes)

    def to_dict(self) -> dict[str, object]:
        return {
            "source": self.source,
            "groups": [
                {
                    "name": v.group.value,
                    "vertices": v.vertex_count,
                    "thickness_cm": round(v.thickness_cm, 3),
                    "chains": len(v.chains),
                }
                for v in self.volumes
            ],
        }


def groups_present(coverage: dict[HairGroup, float], threshold: float = 0.12) -> list[HairGroup]:
    """Which groups the photograph actually supports building.

    A group nobody can see is not built. A bald crown should produce no top
    volume rather than a default one.
    """
    return [group for group, share in coverage.items() if share >= threshold]
