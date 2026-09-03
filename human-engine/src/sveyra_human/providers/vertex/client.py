"""Vertex transport. Phase 8 - not implemented."""

from __future__ import annotations

from sveyra_human.api.errors import NotImplementedYetError


class VertexClient:
    def __init__(self, config: object) -> None:
        self._config = config

    def predict(self, payload: dict[str, object]) -> dict[str, object]:
        raise NotImplementedYetError("Vertex client lands in Phase 8.")
