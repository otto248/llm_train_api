# llm_train_api

大模型训练 API 示例项目，基于 [FastAPI](https://fastapi.tiangolo.com/)。该服务提供了一个简易的训练作业管理接口，可用于演示如何提交、查询、更新和删除训练任务。

## 功能简介

- 创建训练作业，指定模型名称、数据集以及超参数
- 查询单个或全部训练作业信息
- 更新训练作业状态（排队中、运行中、已完成、失败、已取消）
- 删除训练作业

## 快速开始

1. 安装依赖

   ```bash
   pip install -e .[dev]
   ```

2. 启动服务

   ```bash
   uvicorn app.main:app --reload
   ```

3. 打开 `http://127.0.0.1:8000/docs` 查看自动生成的 Swagger 文档并进行接口调试。

## API 文档

以下示例假设服务运行在 `http://127.0.0.1:8000`，使用默认的 `/jobs` 路径。

### 创建训练作业

- **方法 / 路径**：`POST /jobs`
- **功能描述**：创建一个新的训练作业，需指定作业 ID、模型名称、数据集以及训练超参数。
- **请求体**：JSON 对象，字段说明如下：
  | 字段 | 类型 | 说明 |
  | --- | --- | --- |
  | `job_id` | string | 训练作业唯一标识 |
  | `model_name` | string | 训练目标模型名称 |
  | `dataset` | string | 使用的数据集标识 |
  | `hyperparameters` | object | 训练超参数键值对 |
- **响应**：返回创建的训练作业信息。
- **请求示例**：

  ```bash
  curl -X POST "http://127.0.0.1:8000/jobs" \
    -H "Content-Type: application/json" \
    -d '{
          "job_id": "job-001",
          "model_name": "gpt-mini",
          "dataset": "dataset-v1",
          "hyperparameters": {"learning_rate": 0.001, "epochs": 5}
        }'
  ```

- **响应示例**：

  ```json
  {
    "id": "job-001",
    "model_name": "gpt-mini",
    "dataset": "dataset-v1",
    "hyperparameters": {"learning_rate": 0.001, "epochs": 5},
    "status": "queued",
    "created_at": "2024-01-01T12:00:00.000000",
    "updated_at": "2024-01-01T12:00:00.000000",
    "error_message": null
  }
  ```

### 查询全部训练作业

- **方法 / 路径**：`GET /jobs`
- **功能描述**：返回所有训练作业的列表。
- **请求参数**：无。
- **响应**：训练作业对象数组。
- **请求示例**：

  ```bash
  curl "http://127.0.0.1:8000/jobs"
  ```

- **响应示例**：

  ```json
  [
    {
      "id": "job-001",
      "model_name": "gpt-mini",
      "dataset": "dataset-v1",
      "hyperparameters": {"learning_rate": 0.001, "epochs": 5},
      "status": "queued",
      "created_at": "2024-01-01T12:00:00.000000",
      "updated_at": "2024-01-01T12:00:00.000000",
      "error_message": null
    }
  ]
  ```

### 查询单个训练作业

- **方法 / 路径**：`GET /jobs/{job_id}`
- **功能描述**：根据 `job_id` 查询对应的训练作业详情。
- **路径参数**：`job_id`（string）——训练作业唯一标识。
- **响应**：匹配的训练作业对象。
- **请求示例**：

  ```bash
  curl "http://127.0.0.1:8000/jobs/job-001"
  ```

- **响应示例**：同“创建训练作业”章节中的响应示例。

### 更新训练作业状态

- **方法 / 路径**：`PATCH /jobs/{job_id}/status`
- **功能描述**：更新指定训练作业的状态（`queued`、`running`、`succeeded`、`failed`、`cancelled`），可选地附带错误信息。
- **路径参数**：`job_id`（string）。
- **请求体**：JSON 对象，字段说明如下：
  | 字段 | 类型 | 说明 |
  | --- | --- | --- |
  | `status` | string | 新的作业状态，取值为 `queued`、`running`、`succeeded`、`failed`、`cancelled` |
  | `error_message` | string/null | 可选，状态为失败时的错误信息 |
- **响应**：更新后的训练作业对象。
- **请求示例**：

  ```bash
  curl -X PATCH "http://127.0.0.1:8000/jobs/job-001/status" \
    -H "Content-Type: application/json" \
    -d '{"status": "running"}'
  ```

- **响应示例**：

  ```json
  {
    "id": "job-001",
    "model_name": "gpt-mini",
    "dataset": "dataset-v1",
    "hyperparameters": {"learning_rate": 0.001, "epochs": 5},
    "status": "running",
    "created_at": "2024-01-01T12:00:00.000000",
    "updated_at": "2024-01-01T12:05:00.000000",
    "error_message": null
  }
  ```

### 删除训练作业

- **方法 / 路径**：`DELETE /jobs/{job_id}`
- **功能描述**：删除指定的训练作业。
- **路径参数**：`job_id`（string）。
- **响应**：无内容，HTTP 状态码为 `204 No Content`。
- **请求示例**：

  ```bash
  curl -X DELETE "http://127.0.0.1:8000/jobs/job-001"
  ```

## 运行测试

```bash
pytest
```

