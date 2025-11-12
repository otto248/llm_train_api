from __future__ import annotations

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.base import Base, configure_mappers
from app.db.session import engine


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings)
    configure_mappers()
    Base.metadata.create_all(bind=engine)

    app = FastAPI(title=settings.app_name, version="0.2.0")
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/healthz")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
