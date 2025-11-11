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
