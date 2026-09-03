"""What a garment engine is allowed to ask of a body.

Deliberately narrow. Cloth simulation belongs in its own module; this is the
whole surface it needs, so the two can be developed and versioned separately.
"""

from __future__ import annotations

from typing import Protocol


class GarmentBodyInterface(Protocol):
    def get_collision_body(self) -> list[dict[str, object]]:
        """Cheap capsules to collide against, not the visible skin mesh."""
        ...

    def get_measurements(self) -> dict[str, float]:
        ...

    def get_skeleton(self) -> dict[str, object]:
        ...

    def get_surface_mesh(self) -> object:
        ...

    def get_pose(self) -> dict[str, object]:
        ...
