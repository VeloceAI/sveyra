"""Try-on providers.

Selected by configuration. The core engine never imports one.
"""

import os

from sveyra_human.providers.base import TryOnProvider
from sveyra_human.providers.mock.tryon import MockTryOnProvider


def build_provider(name: str | None = None) -> TryOnProvider:
    """Return the configured provider.

    Defaults to the mock so the package works with no credentials at all.
    Switching to Vertex is an environment change, never a code change.
    """
    selected = (name or os.environ.get("TRYON_PROVIDER", "mock")).strip().lower()
    if selected in {"mock", "stub", "none"}:
        return MockTryOnProvider()
    if selected == "vertex":
        from sveyra_human.providers.vertex.tryon import VertexTryOnProvider

        return VertexTryOnProvider()
    raise ValueError(f"Unsupported TRYON_PROVIDER: {selected}")


__all__ = ["MockTryOnProvider", "TryOnProvider", "build_provider"]
