from fastapi import Request

from app.core.config import settings
from app.vision.port import VisionPort
from app.vision.stub import StubVision
from app.vision.vertex import VertexGeminiVision


def build_vision() -> VisionPort:
    backend = settings.vision_backend.lower()
    if backend in {"stub", "memory", "inmemory"}:
        return StubVision()
    if backend in {"vertex", "google"}:
        if not settings.google_cloud_project:
            raise ValueError("GOOGLE_CLOUD_PROJECT is required when VISION_BACKEND=vertex.")
        return VertexGeminiVision(
            project=settings.google_cloud_project,
            location=settings.google_cloud_location,
            model=settings.vertex_vision_model_id,
            timeout_seconds=settings.vision_timeout_seconds,
        )
    raise ValueError(f"Unsupported VISION_BACKEND: {settings.vision_backend}")


def get_vision(request: Request) -> VisionPort:
    return request.app.state.vision
