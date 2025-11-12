from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, ConfigDict


def _env_bool(value: str) -> bool:
    return value.lower() in {"true", "1", "yes", "on"}


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    app_name: str = Field(default="LLM Training Management API")
    api_v1_prefix: str = Field(default="/api/v1")
    training_db_url: str = Field(default="sqlite:///./training.db")
    host_training_dir: Optional[Path] = None
    docker_container_name: Optional[str] = None
    docker_working_dir: Optional[str] = None
    enable_process_launch: bool = False
    default_run_progress: float = 0.05
    api_key_header: str = Field(default="X-API-Key")
    admin_api_key: Optional[str] = None


@lru_cache
def get_settings() -> Settings:
    env = os.environ
    data: Dict[str, Any] = {}
    if (value := env.get("APP_NAME")) is not None:
        data["app_name"] = value
    if (value := env.get("API_V1_PREFIX")) is not None:
        data["api_v1_prefix"] = value
    if (value := env.get("TRAINING_DB_URL")) is not None:
        data["training_db_url"] = value
    if (value := env.get("HOST_TRAINING_DIR")):
        data["host_training_dir"] = Path(value)
    if (value := env.get("DOCKER_CONTAINER_NAME")) is not None:
        data["docker_container_name"] = value or None
    if (value := env.get("DOCKER_WORKING_DIR")) is not None:
        data["docker_working_dir"] = value or None
    if (value := env.get("ENABLE_PROCESS_LAUNCH")) is not None:
        data["enable_process_launch"] = _env_bool(value)
    if (value := env.get("DEFAULT_RUN_PROGRESS")) is not None:
        data["default_run_progress"] = float(value)
    if (value := env.get("API_KEY_HEADER")) is not None:
        data["api_key_header"] = value
    if (value := env.get("ADMIN_API_KEY")) is not None:
        data["admin_api_key"] = value or None
    return Settings(**data)
