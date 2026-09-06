"""Vertex AI try-on provider.

Isolated on purpose: nothing in the body engine may import this package, and a
test in the suite fails the build if anything does.
"""

from sveyra_human.providers.vertex.client import VertexClient
from sveyra_human.providers.vertex.config import VertexConfig
from sveyra_human.providers.vertex.tryon import VertexTryOnProvider

__all__ = ["VertexClient", "VertexConfig", "VertexTryOnProvider"]
