from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def ensure_subpath(base_dir: Path, relative_path: str) -> Path:
    base_dir = base_dir.resolve()
    candidate = (base_dir / relative_path).resolve()
    if base_dir not in candidate.parents and candidate != base_dir:
        raise ValueError(
            f"Path {relative_path} escapes configured base directory {base_dir}"
        )
    return candidate
