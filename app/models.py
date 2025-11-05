from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ProjectStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"
    PAUSED = "paused"


class ProjectCreate(BaseModel):
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
    id: str
    status: ProjectStatus = ProjectStatus.ACTIVE
    created_at: datetime
    updated_at: datetime
    runs_started: int = 0


class LogEntry(BaseModel):
    timestamp: datetime
    level: str
    message: str


class Artifact(BaseModel):
    id: str
    name: str
    type: str
    path: str
    created_at: datetime
    tags: List[str] = Field(default_factory=list)


class Run(BaseModel):
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
    status: RunStatus
    progress: Optional[float] = None
    metrics: Optional[Dict[str, float]] = None


class LogQueryParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=500)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class ArtifactTagRequest(BaseModel):
    tag: str = Field(..., description="Tag to apply to the artifact")


class ArtifactListResponse(BaseModel):
    run_id: str
    artifacts: List[Artifact]


class LogListResponse(BaseModel):
    run_id: str
    total: int
    page: int
    page_size: int
    entries: List[LogEntry]


class ProjectDetail(Project):
    runs: List[Run] = Field(default_factory=list)


class RunDetail(Run):
    pass
