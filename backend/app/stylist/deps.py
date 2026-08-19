from fastapi import Request

from app.core.config import settings
from app.stylist.port import StylistPort
from app.stylist.stub import StubStylist


def build_stylist() -> StylistPort:
    backend = settings.stylist_backend.lower()
    if backend in {"stub", "memory", "inmemory", "deterministic"}:
        return StubStylist()
    raise ValueError(f"Unsupported STYLIST_BACKEND: {settings.stylist_backend}")


def get_stylist(request: Request) -> StylistPort:
    return request.app.state.stylist
