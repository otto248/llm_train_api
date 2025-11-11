"""Application entrypoint for the LLM Training Management API."""

from __future__ import annotations

import logging
from typing import Final

from fastapi import FastAPI

from .api import (
    register_dataset_routes,
    register_deid_routes,
    register_deployment_routes,
    register_health_routes,
    register_project_routes,
    register_train_config_routes,
)
from .utils import ensure_data_directories

APP_TITLE: Final[str] = "LLM Training Management API"
APP_VERSION: Final[str] = "0.1.0"


def create_app() -> FastAPI:
    """Construct and configure the FastAPI application instance."""

    logging.basicConfig(level=logging.INFO)
    ensure_data_directories()
    application = FastAPI(title=APP_TITLE, version=APP_VERSION)
    register_project_routes(application)
    register_deid_routes(application)
    register_deployment_routes(application)
    register_dataset_routes(application)
    register_train_config_routes(application)
    register_health_routes(application)
    return application


app = create_app()


def main() -> None:
    """Launch a development server via uvicorn."""

    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000)


__all__ = ["app", "create_app", "main"]
