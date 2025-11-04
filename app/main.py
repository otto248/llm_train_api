"""Application entry point for the LLM training API."""
from __future__ import annotations

from fastapi import FastAPI

from app.routers import training


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""

    app = FastAPI(title="LLM Training API", version="0.1.0")
    app.include_router(training.router)
    return app


app = create_app()

