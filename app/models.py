from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ProjectStatus(str, Enum):
    """Lifecycle states that a project can be in within the training platform."""
    ACTIVE = "active"
    ARCHIVED = "archived"


class RunStatus(str, Enum):
    """Enumeration of the supported lifecycle states for a training run."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"
    PAUSED = "paused"


class ProjectCreate(BaseModel):
    """Request model used when creating a new project via the public API."""
    name: str
    description: Optional[str] = None
    owner: str
    tags: List[str] = Field(default_factory=list)
    dataset_name: str = Field(
        ..., description="Dataset name or identifier associated with the project"
    )
    training_yaml_name: str = Field(
        ..., description="Training YAML configuration filename for the project"
    )


class Project(ProjectCreate):
    """Read model for project summaries returned from list/detail endpoints."""
    id: str
    status: ProjectStatus = ProjectStatus.ACTIVE
    created_at: datetime
    updated_at: datetime
    runs_started: int = 0


class LogEntry(BaseModel):
    """Structured representation of a single log line emitted by a run."""
    timestamp: datetime
    level: str
    message: str


class Artifact(BaseModel):
    """Metadata describing an artifact generated during a training run."""
    id: str
    name: str
    type: str
    path: str
    created_at: datetime
    tags: List[str] = Field(default_factory=list)


class Run(BaseModel):
    """Primary data model for tracking an individual training run's state."""
    id: str
    project_id: str
    status: RunStatus
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0
    metrics: Dict[str, float] = Field(default_factory=dict)
    start_command: str
    artifacts: List[Artifact] = Field(default_factory=list)
    logs: List[LogEntry] = Field(default_factory=list)
    resume_source_artifact_id: Optional[str] = None


class RunStatusUpdate(BaseModel):
    """Partial update payload allowed when mutating a run's status or metrics."""
    status: RunStatus
    progress: Optional[float] = None
    metrics: Optional[Dict[str, float]] = None


class LogQueryParams(BaseModel):
    """Pagination and filtering parameters accepted when listing run logs."""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=500)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class ArtifactTagRequest(BaseModel):
    """Request payload for tagging an existing artifact with a new label."""
    tag: str = Field(..., description="Tag to apply to the artifact")


class ArtifactListResponse(BaseModel):
    """Response envelope returned when listing artifacts for a run."""
    run_id: str
    artifacts: List[Artifact]


class LogListResponse(BaseModel):
    """Response envelope containing paginated log entries for a run."""
    run_id: str
    total: int
    page: int
    page_size: int
    entries: List[LogEntry]


class ProjectDetail(Project):
    """Extended project representation that includes detailed run information."""
    runs: List[Run] = Field(default_factory=list)


class RunDetail(Run):
    """Alias of :class:`Run` reserved for future expansion of run details."""
