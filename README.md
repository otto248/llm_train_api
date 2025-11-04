# LLM Train API

基于 FastAPI + SQLAlchemy 2.x + Pydantic v2 构建的训练流程管理服务，实现实验管理、Run 管理以及 Checkpoint 标记等核心接口。

## 快速开始

```bash
python -m pip install --upgrade pip setuptools wheel
python -m pip install fastapi "uvicorn[standard]" sqlalchemy "pydantic>=2"
```

完成依赖安装后，可通过以下命令启动本地服务：

```bash
python -m app.main
```

启动后可访问 `http://127.0.0.1:8000/docs` 查看在线接口文档。如果缺少 `uvicorn` 等依赖，程序会给出明确的错误提示。

## 主要接口概览

所有接口均在 `/v1` 前缀下，具体示例如下：

- `POST /v1/experiments`：创建实验，支持 `Idempotency-Key` 幂等键。
- `GET /v1/experiments/{exp_id}/detail`：查询实验详情及历史。
- `POST /v1/experiments/{exp_id}/runs`：提交训练任务。
- `GET /v1/experiments/{exp_id}/runs/{run_id}/status`：查看训练状态和指标。
- `POST /v1/experiments/{exp_id}/runs/{run_id}/cancel`：取消训练并生成 checkpoint。
- `POST /v1/experiments/{exp_id}/runs/{run_id}/resume`：从 checkpoint 断点续训。
- `POST /v1/experiments/{exp_id}/checkpoints/mark`：标记 checkpoint 为候选或发布版本。

数据库默认使用本地 `SQLite` 文件 `app.db`，首次启动会自动创建所需表结构。

接口总览
以下 curl 命令假设 FastAPI 服务运行在 http://127.0.0.1:8000。请按需替换示例中的 EXPERIMENT_ID、RUN_ID 等占位符。接口的字段要求来自 app/schemas.py 中的请求模型定义。各接口的行为实现可在 app/main.py 找到。

1. 创建实验 POST /v1/experiments
可选的 Idempotency-Key 头用于防重复提交，同一键值的请求需保持请求体完全一致。

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

curl "http://127.0.0.1:8000/v1/experiments/EXPERIMENT_ID/detail"
3. 在实验下创建运行 POST /v1/experiments/{experiment_id}/runs
请求体需要提供模型、数据集、超参及资源配置。

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

curl "http://127.0.0.1:8000/v1/experiments/EXPERIMENT_ID/runs/RUN_ID/status"
5. 取消运行 POST /v1/experiments/{experiment_id}/runs/{run_id}/cancel
取消后返回检查点路径；重复取消会复用已有路径。

curl -X POST "http://127.0.0.1:8000/v1/experiments/EXPERIMENT_ID/runs/RUN_ID/cancel"
6. 从检查点续训 POST /v1/experiments/{experiment_id}/runs/{run_id}/resume
需要父运行 ID、检查点路径及可选的超参覆盖。响应会返回新的运行 ID。

curl -X POST "http://127.0.0.1:8000/v1/experiments/EXPERIMENT_ID/runs/RUN_ID/resume" \
  -H "Content-Type: application/json" \
  -d '{
        "ckpt_path": "/ckpts/EXPERIMENT_ID/RUN_ID/epoch-3.pt",
        "override_hyperparams": {"lr": 5e-6},
        "notes": "resume with lower LR"
      }'
7. 标记检查点 POST /v1/experiments/{experiment_id}/checkpoints/mark
用于给运行的某个检查点打标签，可携带发布标记与指标信息。

curl -X POST "http://127.0.0.1:8000/v1/experiments/EXPERIMENT_ID/checkpoints/mark" \
  -H "Content-Type: application/json" \
  -d '{
        "run_id": "RUN_ID",
        "ckpt_path": "/ckpts/EXPERIMENT_ID/RUN_ID/best.pt",
        "tag_type": "candidate_base",
        "release_tag": "release-2024-05",
        "metrics": {"eval_reward": 0.87, "loss": 1.2}
      }'