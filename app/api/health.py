"""Health check endpoint."""

from __future__ import annotations

from typing import Dict

import time

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/healthz")
def health() -> Dict[str, str]:
    """对外暴露的健康检查接口。"""

    return {"status": "ok"}


@router.get("/_internal/health")
def internal_health() -> Dict[str, float]:
    """Internal health probe compatible with the deployment API."""

    return {"status": "ok", "time": time.time()}
