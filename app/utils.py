from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

DATA_ROOT_DIR = Path("/tmp/llm_train_api_data")
DATASETS_DIR = DATA_ROOT_DIR / "datasets"
FILES_DIR = DATA_ROOT_DIR / "files"
UPLOADS_DIR = DATA_ROOT_DIR / "uploads"
TRAIN_CONFIG_DIR = DATA_ROOT_DIR / "train_configs"


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


# Ensure directories exist when the module is imported.
ensure_data_directories()
