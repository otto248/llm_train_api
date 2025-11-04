from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime


def generate_experiment_id() -> str:
    return f"exp_{uuid.uuid4().hex[:8]}"


def generate_run_id() -> str:
    return f"run_{uuid.uuid4().hex[:10]}"


def now_timestamp() -> int:
    return int(datetime.utcnow().timestamp())


def compute_payload_hash(payload: dict) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=("|", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
