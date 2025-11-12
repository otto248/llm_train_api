from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict


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
    dataset_name: str
    training_yaml_name: str


class Project(ProjectCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: ProjectStatus = ProjectStatus.ACTIVE
    created_at: datetime
    updated_at: datetime
    runs_started: int = 0


class LogEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timestamp: datetime
    level: str
    message: str


class Artifact(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    type: str
    path: str
    created_at: datetime
    tags: List[str] = Field(default_factory=list)


class Run(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class ProjectDetail(Project):
    runs: List[Run] = Field(default_factory=list)


class RunDetail(Run):
    pass
