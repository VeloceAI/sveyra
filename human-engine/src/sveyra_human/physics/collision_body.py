"""Cheap collision proxies for garments.

Clothing collides against a few dozen capsules, never against every skin
triangle. Keeping this separate from the visible mesh is what lets a cloth
solver run at interactive rates.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from sveyra_human.body.anatomy import collision_primitives
from sveyra_human.body.parameters import BodyParameters
from sveyra_human.skeleton.model import Skeleton


@dataclass(frozen=True)
class Capsule:
    name: str
    start: np.ndarray
    end: np.ndarray
    radius: float

    def distance_to(self, point: np.ndarray) -> float:
        """Signed distance: negative inside the capsule."""
        axis = self.end - self.start
        length_sq = float(axis @ axis)
        if length_sq < 1e-12:
            return float(np.linalg.norm(point - self.start) - self.radius)
        t = float(np.clip((point - self.start) @ axis / length_sq, 0.0, 1.0))
        closest = self.start + t * axis
        return float(np.linalg.norm(point - closest) - self.radius)

    def contains(self, point: np.ndarray) -> bool:
        return self.distance_to(point) <= 0.0


@dataclass(frozen=True)
class CollisionBody:
    capsules: list[Capsule]

    def __len__(self) -> int:
        return len(self.capsules)

    def distance_to(self, point: np.ndarray) -> float:
        """Distance to the nearest capsule surface."""
        if not self.capsules:
            raise ValueError("collision body has no capsules")
        return min(c.distance_to(point) for c in self.capsules)

    def contains(self, point: np.ndarray) -> bool:
        return any(c.contains(point) for c in self.capsules)

    def to_dict(self) -> list[dict[str, object]]:
        return [
            {
                "name": c.name,
                "kind": "capsule",
                "start": [round(float(v), 4) for v in c.start],
                "end": [round(float(v), 4) for v in c.end],
                "radius": round(c.radius, 4),
            }
            for c in self.capsules
        ]


def build_collision_body(params: BodyParameters, skeleton: Skeleton) -> CollisionBody:
    return CollisionBody(
        capsules=[
            Capsule(
                name=str(p["name"]),
                start=np.array(p["start"], dtype=float),
                end=np.array(p["end"], dtype=float),
                radius=float(p["radius"]),
            )
            for p in collision_primitives(params, skeleton.positions)
        ]
    )
