"""Service layer that stores training jobs in memory."""
from __future__ import annotations

from threading import Lock
from typing import Dict, Iterable, Optional

from app.models import JobStatus, TrainingJob


class JobStore:
    """Thread-safe in-memory store for training jobs."""

    def __init__(self) -> None:
        self._jobs: Dict[str, TrainingJob] = {}
        self._lock = Lock()

    def create(self, job: TrainingJob) -> TrainingJob:
        with self._lock:
            if job.id in self._jobs:
                raise ValueError(f"Job with id '{job.id}' already exists")
            self._jobs[job.id] = job
            return job

    def get(self, job_id: str) -> Optional[TrainingJob]:
        with self._lock:
            return self._jobs.get(job_id)

    def all(self) -> Iterable[TrainingJob]:
        with self._lock:
            return list(self._jobs.values())

    def update_status(
        self, job_id: str, status: JobStatus, *, error_message: Optional[str] = None
    ) -> TrainingJob:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                raise KeyError(job_id)
            job.update_status(status, error_message=error_message)
            return job

    def delete(self, job_id: str) -> None:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(job_id)
            del self._jobs[job_id]

