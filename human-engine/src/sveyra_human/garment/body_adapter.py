"""The body, as a garment engine sees it.

A cloth simulator needs a collision volume, measurements, a skeleton and a
surface. It does not need BodyParameters, cross sections, cages or any of the
reconstruction machinery. This adapter is the whole boundary, so a garment
engine can live in its own repository against a stable, narrow contract.
"""

from __future__ import annotations

from dataclasses import dataclass

from sveyra_human.body.anatomy import measurements
from sveyra_human.body.mesh_deformer import SurfaceMesh
from sveyra_human.body.parameters import BodyParameters
from sveyra_human.physics.collision_body import CollisionBody, build_collision_body
from sveyra_human.skeleton.model import Skeleton


@dataclass
class SveyraBody:
    """Concrete `GarmentBodyInterface`."""

    parameters: BodyParameters
    skeleton: Skeleton
    mesh: SurfaceMesh
    pose: str = "rest"

    def get_collision_body(self) -> list[dict[str, object]]:
        return self.collision().to_dict()

    def collision(self) -> CollisionBody:
        return build_collision_body(self.parameters, self.skeleton)

    def get_measurements(self) -> dict[str, float]:
        return measurements(self.parameters)

    def get_skeleton(self) -> dict[str, object]:
        return self.skeleton.to_dict()

    def get_surface_mesh(self) -> SurfaceMesh:
        return self.mesh

    def get_pose(self) -> dict[str, object]:
        # Only a rest pose exists today. Naming it keeps the contract honest
        # rather than implying posing is supported.
        return {"name": self.pose, "type": "t-pose", "posed": False}
