"""Vertex configuration, read from the environment.

Credentials come from Application Default Credentials or workload identity.
Never from source, and never from a checked-in file.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class VertexConfig:
    project_id: str
    location: str
    model: str

    @classmethod
    def from_env(cls) -> VertexConfig:
        missing = [
            key
            for key in ("VERTEX_PROJECT_ID", "VERTEX_TRYON_MODEL")
            if not os.environ.get(key)
        ]
        if missing:
            raise ValueError(f"missing required environment variables: {', '.join(missing)}")
        return cls(
            project_id=os.environ["VERTEX_PROJECT_ID"],
            location=os.environ.get("VERTEX_LOCATION", "us-central1"),
            model=os.environ["VERTEX_TRYON_MODEL"],
        )
