"""FastAPI router registration."""

from __future__ import annotations

from fastapi import APIRouter

from . import container, datasets, deid, health, projects, train_config, uploads

api_router = APIRouter()
api_router.include_router(projects.router)
api_router.include_router(container.router)
api_router.include_router(deid.router)
api_router.include_router(datasets.router)
api_router.include_router(uploads.router)
api_router.include_router(train_config.router)
api_router.include_router(health.router)

__all__ = ["api_router"]
