from fastapi import Request

from app.core.config import settings
from app.vision.port import VisionPort
from app.vision.stub import StubVision


def build_vision() -> VisionPort:
    backend = settings.vision_backend.lower()
    if backend in {"stub", "memory", "inmemory"}:
        return StubVision()
    raise ValueError(f"Unsupported VISION_BACKEND: {settings.vision_backend}")


def get_vision(request: Request) -> VisionPort:
    return request.app.state.vision
