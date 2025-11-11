"""Application factory for the FastAPI service."""

from __future__ import annotations

from typing import Final

from fastapi import FastAPI

from app.logging import configure_logging
from src.api import register_routers
from src.utils.storage import ensure_data_directories

APP_TITLE: Final[str] = "LLM Training Management API"
APP_VERSION: Final[str] = "0.1.0"


def create_app() -> FastAPI:
    """Construct and configure the FastAPI application instance."""

    configure_logging()
    ensure_data_directories()
    application = FastAPI(title=APP_TITLE, version=APP_VERSION)
    register_routers(application)
    return application


app = create_app()

from main import app, create_app, main as run

__all__ = ["app", "create_app"]
