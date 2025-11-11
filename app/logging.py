"""Logging configuration helpers for the FastAPI application."""

from __future__ import annotations

import logging
from typing import Optional

_DEFAULT_LEVEL = logging.INFO


def configure_logging(level: Optional[int] = None) -> None:
    """Configure root logging with a consistent formatter if not already set."""

    logging.basicConfig(
        level=level or _DEFAULT_LEVEL,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
