"""Centralized configuration for the LLM training API."""

from __future__ import annotations

from pathlib import Path

HOST_TRAINING_DIR = "/data1/qwen2.5-14bxxxx"
DOCKER_CONTAINER_NAME = "qwen2.5-14b-instruct_xpytorch_full_sft"
DOCKER_WORKING_DIR = "KTIP_Release_2.1.0/train/llm"

CONTAINER_FILE_TARGET_DIR = "/mnt/disk"
CONTAINER_FILE_CONTENT = "cym"
LOCAL_DOCKER_CONTAINER_NAME = "mycontainer"

HOST_TRAINING_PATH = Path(HOST_TRAINING_DIR).resolve()

MAX_SMALL_FILE_BYTES = 10 * 1024 * 1024  # 10MB
MAX_YAML_BYTES = 5 * 1024 * 1024  # 5MB
POLICY_VERSION = "2024-01-01"
