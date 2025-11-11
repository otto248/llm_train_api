"""Health check endpoint."""

from __future__ import annotations

from typing import Dict

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/healthz")
def health() -> Dict[str, str]:
    return {"status": "ok"}
