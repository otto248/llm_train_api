from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

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


class ContainerFileRequest(BaseModel):
    """描述在容器内创建文件时需要的输入参数。"""

    filename: str = Field(
        default="cym.txt",
        description="要在目标容器内 /mnt/disk 目录下创建的文件名",
        min_length=1,
    )


class ContainerFileResponse(BaseModel):
    """返回容器内已创建文件的元数据。"""

    path: str = Field(..., description="容器内创建文件的绝对路径")
    content: str = Field(..., description="写入文件的内容")


class DeidRequestOptions(BaseModel):
    """脱敏请求的可选配置项，控制本地化、输出格式等参数。"""

    locale: Optional[str] = "zh-CN"
    format: Optional[str] = "text"
    return_mapping: Optional[bool] = False
    seed: Optional[int] = None


class DeidRequest(BaseModel):
    """发起脱敏任务时的请求体模型，包含文本和策略信息。"""

    policy_id: Optional[str] = "default"
    text: List[str]
    options: Optional[DeidRequestOptions] = DeidRequestOptions()


class DeidResponse(BaseModel):
    """脱敏接口返回的数据结构，包含处理后的文本与映射信息。"""

    deidentified: List[str]
    mapping: Optional[List[Dict[str, str]]] = None
    policy_version: str


class DatasetCreateRequest(BaseModel):
    """创建数据集时提交的请求体模型。"""

    name: str
    dtype: Optional[str] = Field(None, alias="type")
    description: Optional[str] = None
    task_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class DatasetRecord(BaseModel):
    """描述数据集信息的响应模型。"""

    id: str
    name: str
    type: Optional[str] = None
    description: Optional[str] = None
    task_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: str
    status: str
    files: List[Dict[str, Any]] = Field(default_factory=list)


class OperationAction(str, Enum):
    """系统支持记录的操作类型。"""

    CREATE_DATASET = "create_dataset"
    UPLOAD_DATASET_FILE = "upload_dataset_file"
    UPLOAD_TRAIN_CONFIG = "upload_train_config"
    ABORT_UPLOAD = "abort_upload"
    DELETE_DATASET_FILE = "delete_dataset_file"
    DELETE_TRAIN_CONFIG = "delete_train_config"


class OperationTargetType(str, Enum):
    """操作影响的资源类型。"""

    DATASET = "dataset"
    DATASET_FILE = "dataset_file"
    UPLOAD_SESSION = "upload_session"
    TRAIN_CONFIG = "train_config"


class OperationStatus(str, Enum):
    """操作执行结果状态。"""

    SUCCESS = "success"
    FAILURE = "failure"


class OperationLog(BaseModel):
    """记录关键接口操作行为的审计日志模型。"""

    id: str
    action: OperationAction
    target_type: OperationTargetType
    target_id: Optional[str] = None
    status: OperationStatus
    detail: Optional[str] = None
    created_at: datetime
    extra: Dict[str, Any] = Field(default_factory=dict)
