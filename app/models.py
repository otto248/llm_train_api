"""Data models for the LLM training API."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Optional


class JobStatus(str, Enum):
    """Enumeration of possible lifecycle states for a training job."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


@dataclass
class TrainingJob:
    """In-memory representation of a training job."""

    id: str
    model_name: str
    dataset: str
    hyperparameters: Dict[str, float]
    status: JobStatus = JobStatus.QUEUED
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    error_message: Optional[str] = None

    def update_status(self, status: JobStatus, *, error_message: Optional[str] = None) -> None:
        """Update the job status and timestamp."""

        self.status = status
        self.updated_at = datetime.utcnow()
        if error_message:
            self.error_message = error_message

