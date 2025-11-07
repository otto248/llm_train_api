from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ProjectStatus(str, Enum):
    """描述训练平台中项目生命周期的枚举，用于限定项目状态字段。"""
    ACTIVE = "active"
    ARCHIVED = "archived"


class RunStatus(str, Enum):
    """列举训练任务支持的各个生命周期状态，驱动运行状态机。"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"
    PAUSED = "paused"


class ProjectCreate(BaseModel):
    """创建项目时使用的请求体模型，约束必填字段与基础信息。"""
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
    """项目概要响应模型，承载列表与详情接口返回的只读信息。"""
    id: str
    status: ProjectStatus = ProjectStatus.ACTIVE
    created_at: datetime
    updated_at: datetime
    runs_started: int = 0


class LogEntry(BaseModel):
    """运行过程中输出的单条日志结构化记录，包含时间与级别。"""
    timestamp: datetime
    level: str
    message: str


class Artifact(BaseModel):
    """训练运行生成的工件元数据模型，用于标识文件及标签信息。"""
    id: str
    name: str
    type: str
    path: str
    created_at: datetime
    tags: List[str] = Field(default_factory=list)


class Run(BaseModel):
    """记录单次训练运行状态与关联信息的核心数据模型。"""
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
    """更新运行状态或进度时使用的部分更新模型，限制可修改字段。"""
    status: RunStatus
    progress: Optional[float] = None
    metrics: Optional[Dict[str, float]] = None


class LogQueryParams(BaseModel):
    """查询运行日志时支持的分页与时间过滤参数模型。"""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=500)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class ArtifactTagRequest(BaseModel):
    """为已有工件追加标签时使用的请求体模型。"""
    tag: str = Field(..., description="Tag to apply to the artifact")


class ArtifactListResponse(BaseModel):
    """列出运行工件时返回的响应封装，包含运行标识和工件集合。"""
    run_id: str
    artifacts: List[Artifact]


class LogListResponse(BaseModel):
    """返回运行日志列表的响应模型，携带分页信息与日志条目。"""
    run_id: str
    total: int
    page: int
    page_size: int
    entries: List[LogEntry]


class ProjectDetail(Project):
    """在项目概要基础上补充运行列表的详细项目模型。"""
    runs: List[Run] = Field(default_factory=list)


class RunDetail(Run):
    """与 `Run` 相同的运行详情模型，为未来扩展保留命名空间。"""
