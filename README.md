# LLM 训练管理 API

一个基于 FastAPI 的轻量级服务，用于集中管理大模型训练项目、数据集上传、训练配置文件以及模型部署流程。服务将业务按功能域拆分，配合清晰的目录结构，便于多人协作与扩展。

## 项目结构
```
fastapi-app/
├─ app/
│  ├─ __init__.py          # 暴露 FastAPI app 与工厂方法
│  ├─ main.py              # 创建 FastAPI 实例并自动注册路由
│  ├─ config.py            # 全局配置（目录、策略等常量）
│  ├─ deps.py              # FastAPI 依赖定义（数据库、服务）
│  └─ logging.py           # 日志初始化
│
├─ src/
│  ├─ api/                 # 各功能域对外暴露的路由
│  │  ├─ __init__.py       # 统一注册所有路由模块
│  │  ├─ datasets.py       # 数据集与文件上传接口
│  │  ├─ deployments.py    # 模型部署生命周期管理
│  │  ├─ deidentify.py     # 文本脱敏接口
│  │  ├─ health.py         # 健康检查
│  │  ├─ projects.py       # 训练项目与运行管理
│  │  └─ train_configs.py  # 训练配置上传与清理
│  │
│  ├─ schemas/             # Pydantic 数据结构
│  │  └─ __init__.py
│  │
│  ├─ db/                  # SQLAlchemy 元数据与表定义
│  │  ├─ __init__.py
│  │  ├─ base.py
│  │  ├─ models.py
│  │  └─ session.py
│  │
│  ├─ services/            # 业务服务/仓储实现
│  │  ├─ __init__.py
│  │  ├─ data_store.py
│  │  └─ deidentify_service.py
│  │
│  └─ utils/               # 通用工具
│     ├─ __init__.py
│     └─ storage.py        # 本地文件与容器命令辅助
│
├─ main.py                 # 兼容入口，导出 app
├─ requirements.txt
└─ README.md
```

## 核心能力
- **项目管理**：`src/api/projects.py` 暴露项目创建、列表与运行管理接口；`src/services/data_store.py` 通过 SQLAlchemy 维护项目、运行、日志与工件数据。
- **数据集与配置上传**：`src/api/datasets.py` 管理数据集元数据、小文件上传；`src/api/train_configs.py` 负责训练配置 YAML 的上传、查询和删除。
- **部署管理**：`src/api/deployments.py` 以进程方式管理 vLLM 模型服务，支持查询、健康检查以及强制下线。
- **文本脱敏**：`src/api/deidentify.py` 与 `src/services/deidentify_service.py` 提供策略化的脱敏实现，可根据策略 ID 扩展。
- **健康检查**：`src/api/health.py` 提供对外与内部的健康探针，兼容部署管理模块使用的 `_internal/health` 接口。

## 快速开始
1. 安装依赖：`pip install -r requirements.txt`
2. 启动服务：`uvicorn main:app --reload`
3. 使用 `http://localhost:8000/docs` 查看交互式文档。

## 主要接口示例
## 项目结构
```
fastapi-app/
├─ app/
│  ├─ __init__.py              # 暴露 app/create_app
│  ├─ config.py                # 平台常量与限制配置
│  ├─ deps.py                  # FastAPI 依赖注入
│  ├─ logging.py               # 日志初始化入口
│  └─ main.py                  # 应用工厂与路由装配
├─ src/
│  ├─ __init__.py
│  ├─ features/
│  │  ├─ datasets/
│  │  │  ├─ __init__.py
│  │  │  └─ api.py             # 数据集与上传接口
│  │  ├─ deid/
│  │  │  ├─ __init__.py
│  │  │  ├─ api.py             # 脱敏接口
│  │  │  └─ services.py        # 脱敏策略实现
│  │  ├─ deployments/
│  │  │  ├─ __init__.py
│  │  │  └─ api.py             # 模型部署管理
│  │  ├─ health/
│  │  │  ├─ __init__.py
│  │  │  └─ api.py             # 健康检查
│  │  ├─ projects/
│  │  │  ├─ __init__.py
│  │  │  └─ api.py             # 项目与运行管理
│  │  └─ train_configs/
│  │     ├─ __init__.py
│  │     └─ api.py             # 训练配置上传
│  ├─ models/
│  │  └─ __init__.py           # 共享 Pydantic 模型
│  ├─ storage/
│  │  └─ __init__.py           # SQLAlchemy 存储实现
│  └─ utils/
│     └─ filesystem.py         # 本地文件系统工具
├─ main.py                     # 顶层可执行入口
└─ requirements.txt
```

## 功能概览
- **项目管理**：登记训练项目的基本信息（名称、负责人、数据集、训练配置等），并持久化保存。项目默认处于 `active` 状态，可扩展为归档等流程。【F:src/models/__init__.py†L12-L51】【F:src/storage/__init__.py†L67-L123】
- **运行管理**：为任意项目创建新的训练运行，记录启动命令、运行状态、进度、指标及关联系统日志/工件。【F:src/features/projects/api.py†L83-L147】【F:src/storage/__init__.py†L124-L326】
- **日志与工件**：运行创建时自动补充示例日志与工件，便于前端或外部系统演示展示，也支持追加标签、分页查询等存储能力。【F:src/storage/__init__.py†L327-L567】

## API 端点

以下内容按接口列出了请求参数、响应结构以及便于调试的 `curl` 示例。所有端点均返回 Pydantic 模型封装的结构化数据，详细字段定义可参考 `src/models/__init__.py`。【F:src/models/__init__.py†L12-L215】

### 创建项目
- **方法/路径**：`POST /projects`
- **请求体**：`ProjectCreate`
- **响应体**：`ProjectDetail`

```bash
curl -X POST "http://localhost:8000/projects" \
  -H "Content-Type: application/json" \
  -d '{
        "name": "demo-project",
        "description": "微调示例",
        "owner": "alice",
        "tags": ["demo"],
        "dataset_name": "datasets/sample.jsonl",
        "training_yaml_name": "configs/train.yaml"
      }'
```

### 上传数据集文件
- **方法/路径**：`PUT /v1/datasets/{dataset_id}/files`
- **请求体**：`multipart/form-data`
- **响应体**：上传元数据（包含 `upload_id`、大小等信息）

```bash
curl -X PUT "http://localhost:8000/v1/datasets/{dataset_id}/files" \
  -F "file=@sample.jsonl"
```

### 上传训练配置
- **方法/路径**：`PUT /v1/train-config`
- **请求体**：YAML 文件
- **响应体**：上传的元数据

```bash
curl -X PUT "http://localhost:8000/v1/train-config" \
  -F "file=@train.yaml"
```

### 创建部署
- **方法/路径**：`POST /deployments`
- **请求体**：模型路径、可选标签、额外参数等
- **响应体**：`DeploymentInfo`

```bash
curl -X POST "http://localhost:8000/deployments" \
  -H "Content-Type: application/json" \
  -d '{
        "model_path": "/models/qwen",
        "tags": ["demo"],
        "preferred_gpu": 0
      }'
curl -X POST "http://localhost:8000/projects/qwen-finetune/runs"
```

### 文本脱敏
- **方法/路径**：`POST /v1/deidentify:test`
- **请求体**：`DeidRequest`
- **响应体**：`DeidResponse`

```bash
curl -X POST "http://localhost:8000/v1/deidentify:test" \
  -H "Content-Type: application/json" \
  -d '{
        "policy_id": "default",
        "text": ["客户手机号 13812345678"],
        "options": {"return_mapping": true, "seed": 42}
      }'
```

更多字段与返回格式请参考 `src/schemas/__init__.py` 中的 Pydantic 定义。
### 创建数据集元信息
- **方法/路径**：`POST /v1/datasets`
- **请求体**：`DatasetCreateRequest`

```json
{
  "name": "chatglm_pairs_v1",
  "type": "text2text",
  "description": "object-storage",
  "task_type": "sft",
  "metadata": {
    "language": "zh",
    "records": 1024
  }
}
```

- **响应体**：包含新数据集 ID 与创建时间

```json
{
  "id": "93f22d88-9d39-4f71-a3b1-0f41d396a4f7",
  "created_at": "2024-04-12T08:50:31.027Z"
}
```

- **`curl` 示例**

```bash
curl -X POST "http://localhost:8000/v1/datasets" \
  -H "Content-Type: application/json" \
  -d '{
        "name": "chatglm_pairs_v1",
        "type": "text2text",
        "description": "object-storage",
        "task_type": "sft",
        "metadata": {"language": "zh", "records": 1024}
      }'
```

### 查询数据集详情
- **方法/路径**：`GET /v1/datasets/{dataset_id}`
- **路径参数**：`dataset_id`
- **响应体**：`DatasetRecord`（附带上传进度）

```json
{
  "id": "93f22d88-9d39-4f71-a3b1-0f41d396a4f7",
  "name": "chatglm_pairs_v1",
  "type": "text2text",
  "description": "object-storage",
  "task_type": "sft",
  "metadata": {
    "language": "zh",
    "records": 1024
  },
  "created_at": "2024-04-12T08:50:31.027Z",
  "status": "ready",
  "files": [
    {
      "upload_id": "e874d5a8-98f1-4fdb-9055-11e53fd0e936",
      "name": "train.jsonl",
      "stored_name": "e874d5a8-98f1-4fdb-9055-11e53fd0e936_train.jsonl",
      "bytes": 1048576,
      "uploaded_at": "2024-04-12T08:55:02.441Z"
    }
  ],
  "train_config": null,
  "upload_progress": {
    "files_count": 1
  }
}
```

- **`curl` 示例**

```bash
curl "http://localhost:8000/v1/datasets/93f22d88-9d39-4f71-a3b1-0f41d396a4f7"
```

### 上传小文件到数据集
- **方法/路径**：`PUT /v1/datasets/{dataset_id}/files`
- **路径参数**：`dataset_id`
- **请求体**：`multipart/form-data`，字段 `file` 为待上传文件
- **响应体**：包含上传任务 ID 及基础信息

```json
{
  "upload_id": "e874d5a8-98f1-4fdb-9055-11e53fd0e936",
  "dataset_id": "93f22d88-9d39-4f71-a3b1-0f41d396a4f7",
  "bytes": 1048576,
  "filename": "train.jsonl"
}
```

- **`curl` 示例**

```bash
curl -X PUT "http://localhost:8000/v1/datasets/93f22d88-9d39-4f71-a3b1-0f41d396a4f7/files" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@./train.jsonl"
```

### 创建模型部署
- **方法/路径**：`POST /deployments`
- **请求体**：`CreateDeploymentRequest`

```json
{
  "model_path": "models/qwen2.5",
  "model_version": "v1",
  "tags": ["demo"],
  "extra_args": "--max-num-seqs 4",
  "preferred_gpu": 0,
  "health_path": "/health"
}
```

- **响应体**：`DeploymentInfo`

```json
{
  "deployment_id": "16b3f6fe-7047-42bd-89f8-8da30d47eeb5",
  "model_path": "models/qwen2.5",
  "model_version": "v1",
  "tags": ["demo"],
  "gpu_id": 0,
  "port": 8234,
  "pid": 4311,
  "status": "running",
  "started_at": 1712904843.021,
  "stopped_at": null,
  "health_ok": true,
  "vllm_cmd": "vllm --model models/qwen2.5 --http-port 8234 --device-ids 0 --max-num-seqs 4",
  "log_file": "./deploy_logs/16b3f6fe-7047-42bd-89f8-8da30d47eeb5.log",
  "health_path": "/health"
}
```

- **`curl` 示例**

```bash
curl -X POST "http://localhost:8000/deployments" \
  -H "Content-Type: application/json" \
  -d '{
        "model_path": "models/qwen2.5",
        "model_version": "v1",
        "tags": ["demo"],
        "extra_args": "--max-num-seqs 4",
        "preferred_gpu": 0
      }'
```

### 查询模型部署状态
- **方法/路径**：`GET /deployments/{deployment_id}`
- **路径参数**：`deployment_id`
- **响应体**：`DeploymentInfo`

```json
{
  "deployment_id": "16b3f6fe-7047-42bd-89f8-8da30d47eeb5",
  "model_path": "models/qwen2.5",
  "model_version": "v1",
  "tags": ["demo"],
  "gpu_id": 0,
  "port": 8234,
  "pid": 4311,
  "status": "running",
  "started_at": 1712904843.021,
  "stopped_at": null,
  "health_ok": true,
  "vllm_cmd": "vllm --model models/qwen2.5 --http-port 8234 --device-ids 0 --max-num-seqs 4",
  "log_file": "./deploy_logs/16b3f6fe-7047-42bd-89f8-8da30d47eeb5.log",
  "health_path": "/health"
}
```

- **`curl` 示例**

```bash
curl "http://localhost:8000/deployments/16b3f6fe-7047-42bd-89f8-8da30d47eeb5"
```

### 删除模型部署
- **方法/路径**：`DELETE /deployments/{deployment_id}`
- **路径参数**：`deployment_id`
- **查询参数**：`force`（可选，布尔值，进程无法退出时是否强制 `SIGKILL`）
- **响应体**：

```json
{
  "detail": "deployment removed",
  "deployment_id": "16b3f6fe-7047-42bd-89f8-8da30d47eeb5"
}
```

- **`curl` 示例**

```bash
curl -X DELETE "http://localhost:8000/deployments/16b3f6fe-7047-42bd-89f8-8da30d47eeb5?force=true"
```

### 列出模型部署
- **方法/路径**：`GET /deployments`
- **查询参数（可选）**：`model`、`tag`、`status`
- **响应体**：`DeploymentInfo` 数组

```json
[
  {
    "deployment_id": "16b3f6fe-7047-42bd-89f8-8da30d47eeb5",
    "model_path": "models/qwen2.5",
    "model_version": "v1",
    "tags": ["demo"],
    "gpu_id": 0,
    "port": 8234,
    "pid": 4311,
    "status": "running",
    "started_at": 1712904843.021,
    "stopped_at": null,
    "health_ok": true,
    "vllm_cmd": "vllm --model models/qwen2.5 --http-port 8234 --device-ids 0 --max-num-seqs 4",
    "log_file": "./deploy_logs/16b3f6fe-7047-42bd-89f8-8da30d47eeb5.log",
    "health_path": "/health"
  }
]
```

- **`curl` 示例**

```bash
curl "http://localhost:8000/deployments?model=models/qwen2.5&status=running"
```

### 取消文件上传
- **方法/路径**：`DELETE /v1/uploads/{upload_id}`
- **路径参数**：`upload_id`
- **响应体**：

```json
{
  "upload_id": "e874d5a8-98f1-4fdb-9055-11e53fd0e936",
  "status": "aborted"
}
```

- **`curl` 示例**

```bash
curl -X DELETE "http://localhost:8000/v1/uploads/e874d5a8-98f1-4fdb-9055-11e53fd0e936"
```

### 上传训练配置文件
- **方法/路径**：`PUT /v1/train-config`
- **请求体**：`multipart/form-data`，字段 `file` 为 `.yaml/.yml` 文件
- **响应体**：返回上传配置的元信息

```json
{
  "train_config": {
    "filename": "finetune.yaml",
    "uploaded_at": "2024-04-12T08:56:12.871Z",
    "size": 2048
  }
}
```

- **`curl` 示例**

```bash
curl -X PUT "http://localhost:8000/v1/train-config" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@./finetune.yaml"
```

### 获取训练配置文件信息
- **方法/路径**：`GET /v1/train-config`
- **响应体**：当前已上传的配置元信息

```json
{
  "filename": "finetune.yaml",
  "uploaded_at": "2024-04-12T08:56:12.871Z",
  "size": 2048
}
```

- **`curl` 示例**

```bash
curl "http://localhost:8000/v1/train-config"
```

### 删除训练配置文件
- **方法/路径**：`DELETE /v1/train-config`
- **响应体**：

```json
{
  "status": "train_config_deleted"
}
```

- **`curl` 示例**

```bash
curl -X DELETE "http://localhost:8000/v1/train-config"
```

### 健康检查
- **方法/路径**：`GET /healthz`
- **响应体**：

```json
{
  "status": "ok"
}
```

- **`curl` 示例**

```bash
curl "http://localhost:8000/healthz"
```

## 训练命令执行流程
1. **项目资源校验**：创建运行前，会检查项目中声明的 `dataset_name` 与 `training_yaml_name` 是否存在于宿主机的训练目录（默认 `/data1/qwen2.5-14bxxxx`）。若缺失，将返回 400 错误提示缺少的资源。【F:src/features/projects/api.py†L33-L63】
2. **启动命令构建**：服务默认拼接 `bash run_train_full_sft.sh <training_yaml>` 作为启动命令，可根据需要修改 `_build_start_command` 的实现。【F:src/features/projects/api.py†L27-L31】
3. **Docker 内执行**：训练命令通过 `docker exec` 在指定容器（默认 `qwen2.5-14b-instruct_xpytorch_full_sft`）及工作目录（默认 `KTIP_Release_2.1.0/train/llm`）中执行。命令在独立的 bash 会话中启动，标准输出/错误被忽略，可根据需要定制重定向策略。【F:src/utils/filesystem.py†L87-L114】
4. **运行状态更新**：启动成功后，服务会写入确认日志，并将运行状态更新为 `running`，初始进度为 0.05。若命令启动失败，会记录错误日志并将运行标记为 `failed`。【F:src/features/projects/api.py†L98-L147】

> 💡 在部署时，可根据实际环境调整 `_HOST_TRAINING_DIR`、`_DOCKER_CONTAINER_NAME` 与 `_DOCKER_WORKING_DIR` 常量，以匹配真实的宿主机目录与容器名称。【F:app/config.py†L7-L15】

## 快速开始
```bash
# 安装依赖
pip install -r requirements.txt

# 启动开发服务器（默认端口 8000）
uvicorn main:app --reload
```
启动后可通过 <http://localhost:8000/docs> 查看自动生成的 Swagger UI 并调试接口。

### 数据库存储配置
- **默认配置**：若未设置环境变量，服务会使用本地 `sqlite:///./training.db` 文件存储所有项目、运行、日志与工件记录。【F:src/storage/__init__.py†L39-L43】【F:src/storage/__init__.py†L86-L123】
- **自定义数据库**：部署时可设置 `TRAINING_DB_URL` 指向任意兼容 SQLAlchemy 的数据库（如 PostgreSQL、MySQL 等）。服务启动时会自动创建所需的四张表：`projects`、`runs`、`logs`、`artifacts`。【F:src/storage/__init__.py†L39-L83】

## 本地开发建议
1. **准备训练目录**：在宿主机上创建 `_HOST_TRAINING_DIR` 对应的路径，确保示例数据集与训练配置文件存在（或调整常量指向本地测试路径）。【F:app/config.py†L7-L11】【F:src/features/projects/api.py†L33-L63】
2. **验证数据库**：首次运行会自动生成 SQLite 文件；若切换数据库，请确认网络、权限与凭据设置正确。
3. **调试命令执行**：为了安全性，默认训练命令在后台静默运行。需要实时查看日志时，可以修改 `_launch_training_process` 将 `stdout`/`stderr` 重定向到文件或管道。

## 后续扩展方向
- 暴露运行详情、日志分页、工件标签等 API（存储层已具备相关能力）。【F:src/storage/__init__.py†L327-L567】
- 接入任务编排系统或消息队列，实现分布式训练调度。
- 将训练命令执行抽象为接口，以支持不同类型的执行后端（例如 Kubernetes Job、Slurm 等）。

欢迎根据业务需求进行定制与扩展！
