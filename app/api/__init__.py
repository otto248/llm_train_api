"""FastAPI router registration."""

from __future__ import annotations

from fastapi import APIRouter

from . import dataset_upload, deid, deployment, health, project, train_config

api_router = APIRouter()
api_router.include_router(project.router)
api_router.include_router(deid.router)
api_router.include_router(deployment.router)
api_router.include_router(dataset_upload.router)
api_router.include_router(train_config.router)
api_router.include_router(health.router)

__all__ = ["api_router"]
