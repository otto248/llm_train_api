
+79
-32

# LLM Train API

基于 FastAPI + SQLAlchemy 2.x + Pydantic v2 构建的训练流程管理服务，实现实验管理、Run 管理以及 Checkpoint 标记等核心接口。
LLM Train API 是一个基于 **FastAPI**、**SQLAlchemy 2.x** 与 **Pydantic v2** 搭建的训练流程管理服务，用于统一管理实验、运行（Run）以及模型检查点（Checkpoint）的生命周期。项目默认使用 SQLite 数据库，并在首次启动时自动创建数据表。

## 快速开始
## 功能特性
- 实验、运行与检查点的全流程管理接口。
- 幂等的实验创建接口，降低重复提交风险。
- 支持从运行取消到检查点续训的全链路操作。
- 自动初始化本地 SQLite 数据库 `app.db`。

## 环境准备
确保 Python 版本 >= 3.9，推荐创建虚拟环境：

```bash
python -m venv .venv
source .venv/bin/activate  # Windows 使用 .venv\Scripts\activate
```

安装依赖：

```bash
python -m pip install --upgrade pip setuptools wheel
python -m pip install fastapi "uvicorn[standard]" sqlalchemy "pydantic>=2"
```

完成依赖安装后，可通过以下命令启动本地服务：
## 本地运行
安装完成后执行：

```bash
python -m app.main
```

启动后可访问 `http://127.0.0.1:8000/docs` 查看在线接口文档。如果缺少 `uvicorn` 等依赖，程序会给出明确的错误提示。

## 主要接口概览
服务默认监听在 `http://127.0.0.1:8000`，可访问 `http://127.0.0.1:8000/docs` 查看自动生成的交互式接口文档。

所有接口均在 `/v1` 前缀下，具体示例如下：
## API 概览
大多数业务接口均以 `/v1` 为前缀，以下按功能分类：

- `POST /v1/experiments`：创建实验，支持 `Idempotency-Key` 幂等键。
- `GET /v1/experiments/{exp_id}/detail`：查询实验详情及历史。
- `POST /v1/experiments/{exp_id}/runs`：提交训练任务。
- `GET /v1/experiments/{exp_id}/runs/{run_id}/status`：查看训练状态和指标。
- `POST /v1/experiments/{exp_id}/runs/{run_id}/cancel`：取消训练并生成 checkpoint。
- `POST /v1/experiments/{exp_id}/runs/{run_id}/resume`：从 checkpoint 断点续训。
- `POST /v1/experiments/{exp_id}/checkpoints/mark`：标记 checkpoint 为候选或发布版本。
| 功能 | 方法 & 路径 | 说明 |
| --- | --- | --- |
| 创建实验 | `POST /v1/experiments` | 创建新的实验记录，支持 `Idempotency-Key` 幂等键。 |
| 服务元信息 | `GET /` | 返回服务运行提示、OpenAPI 与文档地址。 |
| 查询实验详情 | `GET /v1/experiments/{experiment_id}/detail` | 返回实验元数据、运行摘要与事件记录。 |
| 创建运行 | `POST /v1/experiments/{experiment_id}/runs` | 在实验下提交训练运行。 |
| 查询运行状态 | `GET /v1/experiments/{experiment_id}/runs/{run_id}/status` | 查看运行状态、进度与最新指标。 |
| 取消运行 | `POST /v1/experiments/{experiment_id}/runs/{run_id}/cancel` | 取消运行并生成检查点路径。 |
| 续训运行 | `POST /v1/experiments/{experiment_id}/runs/{run_id}/resume` | 基于检查点创建新的运行。 |
| 标记检查点 | `POST /v1/experiments/{experiment_id}/checkpoints/mark` | 为检查点添加标签、发布标记及指标信息。 |

数据库默认使用本地 `SQLite` 文件 `app.db`，首次启动会自动创建所需表结构。
## curl 调用示例
以下示例假设服务运行在 `http://127.0.0.1:8000`，请根据实际情况替换 `EXPERIMENT_ID`、`RUN_ID` 等占位符。请求/响应模式可参考 `app/schemas.py`，接口实现位于 `app/main.py`。

接口总览
以下 curl 命令假设 FastAPI 服务运行在 http://127.0.0.1:8000。请按需替换示例中的 EXPERIMENT_ID、RUN_ID 等占位符。接口的字段要求来自 app/schemas.py 中的请求模型定义。各接口的行为实现可在 app/main.py 找到。
### 0. 服务元信息
```bash
curl "http://127.0.0.1:8000/"
```

1. 创建实验 POST /v1/experiments
可选的 Idempotency-Key 头用于防重复提交，同一键值的请求需保持请求体完全一致。
返回值会指向 `docs` 与 `openapi.json`，方便快速确认服务是否启动。

### 1. 创建实验
```bash
curl -X POST "http://127.0.0.1:8000/v1/experiments" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: 123e4567-e89b-12d3-a456-426614174000" \
  -d '{
        "name": "My Alignment Study",
        "task_type": "alignment",
        "goal": "Tune RLHF policy",
        "version": "v1",
        "base_model": "gpt-base",
        "owner": "alice@example.com",
        "param_config": {"lr": 3e-5, "batch_size": 64},
        "tags": ["baseline", "rlhf"]
      }'
2. 查询实验详情 GET /v1/experiments/{experiment_id}/detail
返回实验元信息、所有运行摘要及事件历史。
```

### 2. 查询实验详情
```bash
curl "http://127.0.0.1:8000/v1/experiments/EXPERIMENT_ID/detail"
3. 在实验下创建运行 POST /v1/experiments/{experiment_id}/runs
请求体需要提供模型、数据集、超参及资源配置。
```

### 3. 创建运行
```bash
curl -X POST "http://127.0.0.1:8000/v1/experiments/EXPERIMENT_ID/runs" \
  -H "Content-Type: application/json" \
  -d '{
        "model": "gpt-finetune",
        "dataset": {"name": "helpful_dialogue", "split": "train"},
        "hyperparams": {"lr": 1e-5, "epochs": 3},
        "resources": {"gpu_type": "A100", "count": 4},
        "notes": "baseline run"
      }'
4. 查询运行状态 GET /v1/experiments/{experiment_id}/runs/{run_id}/status
返回运行状态、进度与最近指标快照。
```

### 4. 查询运行状态
```bash
curl "http://127.0.0.1:8000/v1/experiments/EXPERIMENT_ID/runs/RUN_ID/status"
5. 取消运行 POST /v1/experiments/{experiment_id}/runs/{run_id}/cancel
取消后返回检查点路径；重复取消会复用已有路径。
```

### 5. 取消运行
```bash
curl -X POST "http://127.0.0.1:8000/v1/experiments/EXPERIMENT_ID/runs/RUN_ID/cancel"
6. 从检查点续训 POST /v1/experiments/{experiment_id}/runs/{run_id}/resume
需要父运行 ID、检查点路径及可选的超参覆盖。响应会返回新的运行 ID。
```

### 6. 从检查点续训
```bash
curl -X POST "http://127.0.0.1:8000/v1/experiments/EXPERIMENT_ID/runs/RUN_ID/resume" \
  -H "Content-Type: application/json" \
  -d '{
        "ckpt_path": "/ckpts/EXPERIMENT_ID/RUN_ID/epoch-3.pt",
        "override_hyperparams": {"lr": 5e-6},
        "notes": "resume with lower LR"
      }'
7. 标记检查点 POST /v1/experiments/{experiment_id}/checkpoints/mark
用于给运行的某个检查点打标签，可携带发布标记与指标信息。
```

### 7. 标记检查点
```bash
curl -X POST "http://127.0.0.1:8000/v1/experiments/EXPERIMENT_ID/checkpoints/mark" \
  -H "Content-Type: application/json" \
  -d '{
        "run_id": "RUN_ID",
        "ckpt_path": "/ckpts/EXPERIMENT_ID/RUN_ID/best.pt",
        "tag_type": "candidate_base",
        "release_tag": "release-2024-05",
        "metrics": {"eval_reward": 0.87, "loss": 1.2}
      }'
      }'
```

## 目录结构
```
.
├── README.md
├── app
│   ├── __init__.py
│   ├── main.py         # FastAPI 应用入口
│   ├── models.py       # SQLAlchemy ORM 模型
│   ├── schemas.py      # Pydantic 数据模型
│   └── services.py     # 业务逻辑与数据库操作
└── pyproject.toml
```

## 更多信息
- 若部署到生产环境，建议使用 `uvicorn` + `gunicorn` 或其它 ASGI Server，并配置持久化数据库。
- 如需补充认证、鉴权或审计日志，可在 `app/services.py` 与 `app/main.py` 基础上扩展。

欢迎根据自身需求进行自定义扩展！