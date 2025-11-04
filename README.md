# LLM Train API

基于 FastAPI + SQLAlchemy 2.x + Pydantic v2 构建的训练流程管理服务，实现实验管理、Run 管理以及 Checkpoint 标记等核心接口。

## 快速开始

```bash
uvicorn app.main:app --reload
```

启动后可访问 `http://127.0.0.1:8000/docs` 查看在线接口文档。

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
