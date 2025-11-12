from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.projects.router import router as project_router

api_router = APIRouter()
api_router.include_router(project_router, prefix="/projects", tags=["projects"])
