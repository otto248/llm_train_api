from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

DATA_ROOT_DIR = Path("/tmp/llm_train_api_data")
DATASETS_DIR = DATA_ROOT_DIR / "datasets"
FILES_DIR = DATA_ROOT_DIR / "files"
UPLOADS_DIR = DATA_ROOT_DIR / "uploads"
TRAIN_CONFIG_DIR = DATA_ROOT_DIR / "train_configs"
TRAIN_CONFIG_METADATA_PATH = TRAIN_CONFIG_DIR / "train_config_metadata.json"
TRAIN_CONFIG_FILENAME = "train_config.yaml"


def ensure_data_directories() -> None:
    """Ensure that all application data directories exist."""
    for directory in (
        DATA_ROOT_DIR,
        DATASETS_DIR,
        FILES_DIR,
        UPLOADS_DIR,
        TRAIN_CONFIG_DIR,
    ):
        directory.mkdir(parents=True, exist_ok=True)


def dataset_path(dataset_id: str) -> Path:
    """Return the filesystem path for the dataset metadata JSON file."""
    return DATASETS_DIR / f"{dataset_id}.json"


def save_dataset_record(record: Dict[str, Any]) -> None:
    """Persist a dataset record to disk using its identifier as the filename."""
    dataset_id = record.get("id")
    if not dataset_id:
        raise ValueError("Dataset record must include an 'id' field")
    normalized = dict(record)
    normalized.setdefault("files", [])
    normalized.setdefault("train_config", None)
    with open(dataset_path(dataset_id), "w", encoding="utf-8") as file_obj:
        json.dump(normalized, file_obj, ensure_ascii=False, indent=2)


def load_dataset_record(dataset_id: str) -> Dict[str, Any]:
    """Load a dataset record from disk."""
    record_path = dataset_path(dataset_id)
    if not record_path.exists():
        raise FileNotFoundError()
    with open(record_path, "r", encoding="utf-8") as file_obj:
        return json.load(file_obj)


def train_config_path() -> Path:
    """Return the canonical filesystem path for the uploaded train config."""

    return TRAIN_CONFIG_DIR / TRAIN_CONFIG_FILENAME


def save_train_config_metadata(metadata: Dict[str, Any]) -> None:
    """Persist train config metadata to disk."""

    with open(TRAIN_CONFIG_METADATA_PATH, "w", encoding="utf-8") as file_obj:
        json.dump(metadata, file_obj, ensure_ascii=False, indent=2)


def load_train_config_metadata() -> Dict[str, Any]:
    """Load train config metadata from disk."""

    if not TRAIN_CONFIG_METADATA_PATH.exists():
        raise FileNotFoundError()
    with open(TRAIN_CONFIG_METADATA_PATH, "r", encoding="utf-8") as file_obj:
        return json.load(file_obj)


def delete_train_config_metadata() -> None:
    """Remove persisted train config metadata if present."""

    try:
        TRAIN_CONFIG_METADATA_PATH.unlink()
    except FileNotFoundError:
        return


def launch_training_process(
    start_command: str,
    *,
    host_training_dir: str,
    docker_container_name: str,
    docker_working_dir: str,
    log: Optional[logging.Logger] = None,
) -> subprocess.Popen[bytes]:
    """Launch a training process inside a Docker container."""

    logger = log or logging.getLogger(__name__)
    docker_command = (
        f"cd {host_training_dir} && "
        f"docker exec -i {docker_container_name} "
        "env LANG=C.UTF-8 bash -lc "
        f"\"cd {docker_working_dir} && {start_command}\""
    )
    logger.info("Launching training command: %s", docker_command)
    try:
        process = subprocess.Popen(  # noqa: S603, S607 - intentional command execution
            ["bash", "-lc", docker_command],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except FileNotFoundError as exc:  # pragma: no cover - defensive guard
        raise RuntimeError("无法执行训练命令，请检查服务器环境配置。") from exc
    return process


def run_container_command(
    container_name: str,
    command: str,
    *,
    log: Optional[logging.Logger] = None,
) -> None:
    """Execute a shell command inside a Docker container."""

    logger = log or logging.getLogger(__name__)
    docker_command = [
        "docker",
        "exec",
        "-i",
        container_name,
        "bash",
        "-lc",
        command,
    ]
    result = subprocess.run(  # noqa: S603, S607 - intentional command execution
        docker_command,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        logger.error(
            "Failed to run command in container %s: %s", container_name, stderr
        )
        raise RuntimeError(
            f"无法在容器 {container_name} 中执行命令：{stderr or '未知错误'}"
        )


# Ensure directories exist when the module is imported.
ensure_data_directories()
