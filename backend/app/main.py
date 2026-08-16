from fastapi import FastAPI

from app.routes.health_routes import router as health_router
from app.routes.profile_routes import router as profile_router


def create_app() -> FastAPI:
    app = FastAPI(title="SVEYRA API", version="0.1.0")
    app.include_router(health_router)
    app.include_router(profile_router, prefix="/v1")
    return app


app = create_app()
