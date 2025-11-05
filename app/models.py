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


class TrainMethod(str, Enum):
    SFT = "SFT"
    LORA = "LoRA"
    RF = "RF"


class SFTHyperParameters(BaseModel):
    learning_rate: float = Field(..., gt=0, description="Learning rate used for supervised fine-tuning")
    batch_size: int = Field(..., gt=0, description="Batch size for gradient updates")
    epochs: int = Field(..., gt=0, description="Number of epochs for supervised training")
    max_seq_length: Optional[int] = Field(
        None,
        gt=0,
        description="Optional maximum sequence length for tokenization",
    )


class LoRAHyperParameters(BaseModel):
    learning_rate: float = Field(..., gt=0, description="Learning rate for LoRA adapters")
    rank: int = Field(..., gt=0, description="LoRA rank controlling adapter capacity")
    alpha: int = Field(..., gt=0, description="Scaling factor applied to the LoRA updates")
    dropout: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Dropout probability applied to LoRA adapters",
    )
    target_modules: List[str] = Field(
        default_factory=list,
        description="List of module names where LoRA adapters are injected",
    )


class RFHyperParameters(BaseModel):
    learning_rate: float = Field(..., gt=0, description="Learning rate for reinforcement fine-tuning")
    kl_coefficient: float = Field(..., gt=0, description="KL penalty coefficient for PPO updates")
    rollout_batch_size: int = Field(
        ..., gt=0, description="Batch size used when collecting rollouts"
    )
    train_batch_size: int = Field(..., gt=0, description="Batch size for PPO optimizer updates")
    reward_model: str = Field(..., description="Identifier of the reward model used for scoring")


class TrainMethodHyperParameters(BaseModel):
    sft: Optional[SFTHyperParameters] = Field(
        default=None,
        description="Default hyperparameters applied when using supervised fine-tuning",
    )
    lora: Optional[LoRAHyperParameters] = Field(
        default=None, description="Default hyperparameters applied when using LoRA"
    )
    rf: Optional[RFHyperParameters] = Field(
        default=None,
        description="Default hyperparameters applied when using reinforcement fine-tuning",
    )


class RunResourceConfig(BaseModel):
    nodes: int = Field(..., ge=1, description="Number of compute nodes to allocate")
    gpus_per_node: int = Field(..., ge=0, description="Number of GPUs per node")
    cpus_per_node: int = Field(..., ge=1, description="Number of CPUs per node")
    memory_gb: int = Field(..., ge=1, description="Memory in GB per node")


class RunHyperParameters(BaseModel):
    learning_rate: float = Field(..., gt=0)
    batch_size: int = Field(..., gt=0)
    epochs: int = Field(..., gt=0)
    optimizer: str
    extra: Dict[str, str] = Field(default_factory=dict)


class RunConfig(BaseModel):
    model: str
    dataset: str
    hyperparameters: RunHyperParameters
    resources: RunResourceConfig
    notes: Optional[str] = None


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    objective: str
    task_type: str
    base_model: str
    owner: str
    tags: List[str] = Field(default_factory=list)
    train_method: TrainMethod = Field(
        default=TrainMethod.SFT, description="Training methodology, e.g. SFT, LoRA, or RF"
    )
    default_hyperparameters: TrainMethodHyperParameters = Field(
        default_factory=TrainMethodHyperParameters,
        description="Default hyperparameter configuration grouped by training method",
    )


class Project(ProjectCreate):
    id: str
    status: ProjectStatus = ProjectStatus.ACTIVE
    created_at: datetime
    updated_at: datetime
    runs_started: int = 0


class RunCreate(BaseModel):
    config: RunConfig


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
    config: RunConfig
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


class ResumeRunRequest(BaseModel):
    artifact_id: str
    additional_epochs: Optional[int] = None
    updated_hyperparameters: Optional[RunHyperParameters] = None


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
