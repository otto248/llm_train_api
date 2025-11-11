"""Application entrypoint for the LLM Training Management API."""

from __future__ import annotations

import logging

from fastapi import FastAPI

from .api import api_router
from .utils import ensure_data_directories

logging.basicConfig(level=logging.INFO)

ensure_data_directories()

app = FastAPI(title="LLM Training Management API", version="0.1.0")
app.include_router(api_router)

__all__ = ["app"]
