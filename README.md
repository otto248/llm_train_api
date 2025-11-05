# LLM 训练管理 API

本仓库提供了一个基于 FastAPI 的服务，用于管理大语言模型（LLM）训练项目及其生命周期。该服务覆盖了从定义训练项目，到发起、监控、取消、恢复训练运行，以及管理生成的工件等完整工作流。

## 目录
- [功能亮点](#功能亮点)
- [架构概览](#架构概览)
  - [目录结构](#目录结构)
  - [模块职责](#模块职责)
  - [请求处理流程](#请求处理流程)
  - [扩展建议](#扩展建议)
- [快速开始](#快速开始)
- [运行 API](#运行-api)
- [API 参考](#api-参考)
  - [创建项目](#创建项目)
  - [列出项目](#列出项目)
  - [获取项目详情](#获取项目详情)
  - [创建训练运行](#创建训练运行)
  - [获取运行详情](#获取运行详情)
  - [取消运行](#取消运行)
  - [获取运行日志](#获取运行日志)
  - [列出运行工件](#列出运行工件)
  - [恢复运行](#恢复运行)
  - [为工件打标签](#为工件打标签)
- [内存存储行为](#内存存储行为)
- [开发提示](#开发提示)

## 功能亮点
- 定义项目元数据，例如名称、描述、目标、任务类型、基线模型和负责人（需求 5.2.1）。
- 查看项目状态、运行次数、默认配置、版本历史和关联的运行（需求 5.2.2）。
- 启动新的训练运行，包括模型、数据集、超参数和资源配置（需求 5.2.3）。
- 监控训练进度，包括状态、指标、时间戳和 GPU 使用情况（需求 5.2.4）。
- 取消正在运行的训练，同时保留最新的检查点（需求 5.2.5）。
- 获取支持分页和时间过滤的日志（需求 5.2.6）。
- 列出工件（检查点、TensorBoard 日志、评估结果、配置文件）（需求 5.2.7）。
- 从选定的检查点恢复训练（需求 5.2.8）。
- 将检查点标记为候选基线模型或发布版本（需求 5.2.9）。

## 架构概览
LLM 训练管理 API 保持了极简但清晰的三层结构：路由层、领域模型层与存储层。你可以通过下文了解代码如何组织与协作。

### 目录结构
```
app/
├── __init__.py          # 标记包，方便后续拓展子模块
├── main.py              # 应用入口，暴露 FastAPI 实例并挂载所有路由
├── models.py            # Pydantic 数据模型，确保请求/响应结构一致
└── storage.py           # InMemoryStorage，模拟持久化与调度行为
```

### 模块职责
| 模块 | 关键职责 | 代表对象/函数 |
| --- | --- | --- |
| `app.main` | 初始化 FastAPI、注册路由、定义依赖注入。 | `app`, `get_storage`, 各类路由处理函数 |
| `app.models` | 描述领域实体，提供请求体验证、响应序列化以及默认值。 | `ProjectCreate`, `Run`, `Artifact`, `PaginatedLogs` 等 |
| `app.storage` | 模拟数据库 + 任务编排：生成 ID、维护项目状态、虚拟化日志/指标/工件。 | `InMemoryStorage`, `create_project`, `create_run`, `cancel_run` |

> **提示：** `InMemoryStorage` 使用 Python 内存保存所有数据，服务重启会导致信息丢失，适合演示或单元测试阶段。

### 请求处理流程
1. **HTTP 入口**：客户端调用 REST 接口，FastAPI 在 `app.main` 中匹配路由。
2. **请求解析**：请求体会被对应的 Pydantic 模型（定义在 `app.models`）自动校验并转化为 Python 对象。
3. **业务逻辑**：路由函数通过依赖注入 (`Depends(get_storage)`) 获取 `InMemoryStorage` 实例并执行增删改查逻辑。
4. **响应生成**：操作结果再度通过模型序列化为 JSON，统一的状态码由 FastAPI 自动处理。

### 扩展建议
- **持久化**：将 `InMemoryStorage` 替换为数据库实现（如 PostgreSQL、MongoDB），同时把任务调度对接到真实的队列/编排器。
- **服务拆分**：当业务增长时，可将路由按领域拆分为独立模块（如 `routers/projects.py`），并引入分层服务类以复用业务逻辑。
- **观测性**：在路由层添加日志、追踪与指标收集钩子，便于集成 Prometheus 或 OpenTelemetry。
- **配置管理**：通过环境变量或配置文件（如 `pydantic-settings`）管理存储后端、认证开关等环境信息。

## 快速开始
安装依赖（推荐使用 Python 3.10 及以上版本）：

```bash
pip install -r requirements.txt
```

可选的快速语法检查：

```bash
python -m compileall app
```

## 运行 API
启动开发服务器：

```bash
uvicorn app.main:app --reload
```

OpenAPI/Swagger UI 可通过 <http://localhost:8000/docs> 访问。你也可以使用 Postman 或任意 HTTP 客户端与 API 交互。

## API 参考
所有端点均返回 JSON 响应并使用标准 HTTP 状态码。除非另有说明，请以 JSON 格式提交请求体。

### 创建项目
- **方法与路径：** `POST /projects`
- **功能描述：** 创建一个新的训练项目并保存其元数据（需求 5.2.1）。
- **入参：**
  - **路径参数：** 无。
  - **查询参数：** 无。
  - **请求体（JSON）：**

    | 字段 | 类型 | 必填 | 说明 |
    | --- | --- | --- | --- |
    | `name` | string | 是 | 项目名称，需全局唯一。 |
    | `description` | string | 否 | 项目摘要，用于说明背景与需求。 |
    | `objective` | string | 否 | 训练目标或关键指标。 |
    | `task_type` | string | 否 | 任务类型，例如“文本摘要”“问答”。 |
    | `base_model` | string | 否 | 训练所基于的模型。 |
    | `owner` | string | 是 | 负责人名称或工号。 |
    | `tags` | array[string] | 否 | 自定义标签，便于分类检索。 |
    | `default_hyperparameters` | object | 否 | 默认超参数配置，键值对形式。 |

  - **示例请求体：**
    ```json
    {
      "name": "中文摘要系统",
      "description": "对科研文章进行自动摘要",
      "objective": "降低阅读时间",
      "task_type": "文本摘要",
      "base_model": "llama-2-13b",
      "owner": "小李",
      "tags": ["科研", "第一阶段"],
      "default_hyperparameters": {
        "learning_rate": 3e-5,
        "batch_size": 16
      }
    }
    ```
- **出参：** `201 Created`
  - **响应体字段：**

    | 字段 | 类型 | 说明 |
    | --- | --- | --- |
    | `id` | string | 项目唯一标识，形如 `proj_xxx`。 |
    | `name` | string | 项目名称。 |
    | `status` | string | 当前状态，示例：`草稿` `进行中`。 |
    | `objective` | string | 训练目标。 |
    | `task_type` | string | 任务类型。 |
    | `base_model` | string | 基线模型。 |
    | `owner` | string | 负责人。 |
    | `created_at` | datetime | 创建时间（ISO 8601）。 |
    | `updated_at` | datetime | 更新时间（ISO 8601）。 |
    | `tags` | array[string] | 标签列表。 |
    | `default_hyperparameters` | object | 默认超参数。 |
    | `runs` | array[object] | 与项目关联的运行列表。 |

  - **响应示例：**
    ```json
    {
      "id": "proj_xxx",
      "name": "中文摘要系统",
      "status": "草稿",
      "objective": "降低阅读时间",
      "task_type": "文本摘要",
      "base_model": "llama-2-13b",
      "owner": "小李",
      "created_at": "2024-01-01T12:00:00Z",
      "updated_at": "2024-01-01T12:00:00Z",
      "tags": ["科研", "第一阶段"],
      "default_hyperparameters": {"learning_rate": 3e-5, "batch_size": 16},
      "runs": []
    }
    ```
- **curl 示例：**
  ```bash
  curl -X POST "http://localhost:8000/projects" \
    -H "Content-Type: application/json" \
    -d '{
          "name": "中文摘要系统",
          "description": "对科研文章进行自动摘要",
          "objective": "降低阅读时间",
          "task_type": "文本摘要",
          "base_model": "llama-2-13b",
          "owner": "小李",
          "tags": ["科研", "第一阶段"],
          "default_hyperparameters": {
            "learning_rate": 3e-5,
            "batch_size": 16
          }
        }'
  ```

### 列出项目
- **方法与路径：** `GET /projects`
- **功能描述：** 获取所有项目的摘要列表。
- **入参：**
  - **路径参数：** 无。
  - **查询参数：**

    | 名称 | 类型 | 必填 | 默认值 | 说明 |
    | --- | --- | --- | --- | --- |
    | `owner` | string | 否 | `null` | 按负责人过滤项目。 |
    | `status` | string | 否 | `null` | 按状态过滤，如 `草稿` `运行中`。 |

    > 若未提供过滤条件，则返回全部项目。
- **出参：** `200 OK`
  - **响应体：** 项目对象数组，每个对象包含：

    | 字段 | 类型 | 说明 |
    | --- | --- | --- |
    | `id` | string | 项目唯一标识。 |
    | `name` | string | 项目名称。 |
    | `status` | string | 项目状态。 |
    | `owner` | string | 负责人。 |
    | `created_at` | datetime | 创建时间。 |

  - **响应示例：**
    ```json
    [
      {
        "id": "proj_xxx",
        "name": "中文摘要系统",
        "status": "草稿",
        "owner": "小李",
        "created_at": "2024-01-01T12:00:00Z"
      }
    ]
    ```
- **curl 示例：**
  ```bash
  curl "http://localhost:8000/projects?owner=%E5%B0%8F%E6%9D%8E"
  ```

### 获取项目详情
- **方法与路径：** `GET /projects/{project_id}`
- **功能描述：** 查看指定项目的全部信息（需求 5.2.2）。
- **入参：**
  - **路径参数：**

    | 名称 | 类型 | 必填 | 说明 |
    | --- | --- | --- | --- |
    | `project_id` | string | 是 | 目标项目的唯一标识，例如 `proj_xxx`。 |
- **出参：** `200 OK`
  - **响应体字段：** 与 [创建项目](#创建项目) 的响应体一致，并包含已存在运行的精简信息。
  - **响应示例：**
    ```json
    {
      "id": "proj_xxx",
      "name": "中文摘要系统",
      "status": "草稿",
      "objective": "降低阅读时间",
      "task_type": "文本摘要",
      "base_model": "llama-2-13b",
      "owner": "小李",
      "created_at": "2024-01-01T12:00:00Z",
      "updated_at": "2024-01-02T09:30:00Z",
      "tags": ["科研", "第一阶段"],
      "default_hyperparameters": {"learning_rate": 3e-5, "batch_size": 16},
      "runs": [
        {
          "id": "run_001",
          "name": "run-001",
          "status": "运行中",
          "progress": 0.42,
          "started_at": "2024-01-02T08:00:00Z"
        }
      ]
    }
    ```
- **curl 示例：**
  ```bash
  curl "http://localhost:8000/projects/proj_xxx"
  ```

### 创建训练运行
- **方法与路径：** `POST /projects/{project_id}/runs`
- **功能描述：** 为项目创建新的训练运行（需求 5.2.3）。
- **入参：**
  - **路径参数：**

    | 名称 | 类型 | 必填 | 说明 |
    | --- | --- | --- | --- |
    | `project_id` | string | 是 | 目标项目的唯一标识。 |

  - **请求体（JSON）：**

    | 字段 | 类型 | 必填 | 说明 |
    | --- | --- | --- | --- |
    | `name` | string | 否 | 运行名称，未提供时系统可回退到默认命名。 |
    | `model` | string | 是 | 本次训练所使用或微调的模型。 |
    | `dataset` | string | 是 | 数据集名称或路径。 |
    | `hyperparameters` | object | 否 | 训练超参数，如学习率、批大小。 |
    | `resources` | object | 否 | 资源配置，例如 GPU 类型与数量。 |

  - **示例请求体：**
    ```json
    {
      "name": "run-001",
      "model": "llama-2-13b",
      "dataset": "中文科技论文语料",
      "hyperparameters": {
        "learning_rate": 2e-5,
        "batch_size": 32,
        "num_epochs": 3
      },
      "resources": {
        "gpu_type": "A100",
        "gpu_count": 4
      }
    }
    ```
- **出参：** `201 Created`
  - **响应体字段：**

    | 字段 | 类型 | 说明 |
    | --- | --- | --- |
    | `id` | string | 运行唯一标识，例如 `run_001`。 |
    | `project_id` | string | 所属项目 ID。 |
    | `name` | string | 运行名称。 |
    | `status` | string | 当前状态，初始为 `排队中`。 |
    | `progress` | float | 运行进度（0–1）。 |
    | `started_at` | datetime/null | 启动时间。 |
    | `artifacts` | array[object] | 初始为空的工件列表。 |

  - **响应示例：**
    ```json
    {
      "id": "run_001",
      "project_id": "proj_xxx",
      "name": "run-001",
      "status": "排队中",
      "progress": 0.0,
      "started_at": null,
      "artifacts": []
    }
    ```
- **curl 示例：**
  ```bash
  curl -X POST "http://localhost:8000/projects/proj_xxx/runs" \
    -H "Content-Type: application/json" \
    -d '{
          "name": "run-001",
          "model": "llama-2-13b",
          "dataset": "中文科技论文语料",
          "hyperparameters": {
            "learning_rate": 2e-5,
            "batch_size": 32,
            "num_epochs": 3
          },
          "resources": {
            "gpu_type": "A100",
            "gpu_count": 4
          }
        }'
  ```

### 获取运行详情
- **方法与路径：** `GET /projects/{project_id}/runs/{run_id}`
- **功能描述：** 查看指定运行的状态与指标（需求 5.2.4）。
- **入参：**
  - **路径参数：**

    | 名称 | 类型 | 必填 | 说明 |
    | --- | --- | --- | --- |
    | `project_id` | string | 是 | 所属项目 ID。 |
    | `run_id` | string | 是 | 运行 ID。 |
- **出参：** `200 OK`
  - **响应体字段：**

    | 字段 | 类型 | 说明 |
    | --- | --- | --- |
    | `id` | string | 运行唯一标识。 |
    | `project_id` | string | 所属项目 ID。 |
    | `name` | string | 运行名称。 |
    | `status` | string | 当前状态，例如 `排队中` `运行中` `已完成`。 |
    | `progress` | float | 当前进度（0–1）。 |
    | `metrics` | object | 指标字典，如损失、准确率。 |
    | `started_at` | datetime | 启动时间。 |
    | `updated_at` | datetime | 最近更新时间。 |
    | `gpu_utilization` | float | GPU 利用率（0–1），模拟数据。 |
    | `artifacts` | array[object] | 生成的工件概览。 |

  - **响应示例：**
    ```json
    {
      "id": "run_001",
      "project_id": "proj_xxx",
      "name": "run-001",
      "status": "运行中",
      "progress": 0.65,
      "metrics": {
        "train_loss": 1.72,
        "eval_rouge_l": 38.4
      },
      "started_at": "2024-01-02T08:05:00Z",
      "updated_at": "2024-01-02T10:15:00Z",
      "gpu_utilization": 0.83
    }
    ```
- **curl 示例：**
  ```bash
  curl "http://localhost:8000/projects/proj_xxx/runs/run_001"
  ```

### 取消运行
- **方法与路径：** `POST /projects/{project_id}/runs/{run_id}/cancel`
- **功能描述：** 取消正在执行的运行并保存最新检查点（需求 5.2.5）。
- **入参：**
  - **路径参数：**

    | 名称 | 类型 | 必填 | 说明 |
    | --- | --- | --- | --- |
    | `project_id` | string | 是 | 所属项目 ID。 |
    | `run_id` | string | 是 | 运行 ID。 |
- **出参：** `200 OK`
  - **响应体字段：**

    | 字段 | 类型 | 说明 |
    | --- | --- | --- |
    | `id` | string | 被取消的运行 ID。 |
    | `project_id` | string | 所属项目 ID。 |
    | `name` | string | 运行名称。 |
    | `status` | string | 状态将更新为 `已取消`。 |
    | `progress` | float | 取消时的进度。 |
    | `cancelled_at` | datetime | 取消时间。 |
    | `artifacts` | array[object] | 包含取消后生成的检查点等工件。 |

  - **响应示例：**
    ```json
    {
      "id": "run_001",
      "project_id": "proj_xxx",
      "name": "run-001",
      "status": "已取消",
      "progress": 0.7,
      "cancelled_at": "2024-01-02T11:00:00Z",
      "artifacts": [
        {
          "id": "ckpt_cancel",
          "name": "取消前的检查点",
          "type": "checkpoint",
          "path": "s3://artifacts/proj_xxx/run_001/ckpt_cancel.pt",
          "created_at": "2024-01-02T11:00:00Z"
        }
      ]
    }
    ```
- **curl 示例：**
  ```bash
  curl -X POST "http://localhost:8000/projects/proj_xxx/runs/run_001/cancel"
  ```

### 获取运行日志
- **方法与路径：** `GET /projects/{project_id}/runs/{run_id}/logs`
- **功能描述：** 获取运行日志，支持分页与可选的时间范围过滤（需求 5.2.6）。
- **入参：**
  - **路径参数：**

    | 名称 | 类型 | 必填 | 说明 |
    | --- | --- | --- | --- |
    | `project_id` | string | 是 | 所属项目 ID。 |
    | `run_id` | string | 是 | 运行 ID。 |

  - **查询参数：**

    | 名称 | 类型 | 必填 | 默认值 | 说明 |
    | --- | --- | --- | --- | --- |
    | `page` | integer | 否 | `1` | 页码（从 1 开始）。 |
    | `page_size` | integer | 否 | `50` | 每页日志数量（1–500）。 |
    | `start_time` | datetime | 否 | `null` | 筛选在此时间或之后的日志。 |
    | `end_time` | datetime | 否 | `null` | 筛选在此时间之前的日志。 |

- **出参：** `200 OK`
  - **响应体字段：**

    | 字段 | 类型 | 说明 |
    | --- | --- | --- |
    | `page` | integer | 当前页码。 |
    | `page_size` | integer | 每页日志数。 |
    | `total` | integer | 总日志条目数。 |
    | `items` | array[object] | 日志条目数组。 |
    | `items[].timestamp` | datetime | 日志时间。 |
    | `items[].level` | string | 日志级别，如 `INFO`。 |
    | `items[].message` | string | 日志内容。 |

  - **响应示例：**
    ```json
    {
      "page": 1,
      "page_size": 50,
      "total": 120,
      "items": [
        {
          "timestamp": "2024-01-02T10:00:00Z",
          "level": "INFO",
          "message": "第 500 步 - loss=1.86 lr=2e-5"
        }
      ]
    }
    ```
- **curl 示例：**
  ```bash
  curl "http://localhost:8000/projects/proj_xxx/runs/run_001/logs?page=2&page_size=20"
  ```

### 列出运行工件
- **方法与路径：** `GET /projects/{project_id}/runs/{run_id}/artifacts`
- **功能描述：** 列出运行生成的检查点和其他输出（需求 5.2.7）。
- **入参：**
  - **路径参数：**

    | 名称 | 类型 | 必填 | 说明 |
    | --- | --- | --- | --- |
    | `project_id` | string | 是 | 所属项目 ID。 |
    | `run_id` | string | 是 | 运行 ID。 |
- **出参：** `200 OK`
  - **响应体字段：**

    | 字段 | 类型 | 说明 |
    | --- | --- | --- |
    | `items` | array[object] | 工件对象列表。 |
    | `items[].id` | string | 工件 ID，例如 `ckpt_001`。 |
    | `items[].name` | string | 工件名称。 |
    | `items[].type` | string | 工件类型，例如 `checkpoint`、`event`。 |
    | `items[].path` | string | 工件的存储路径。 |
    | `items[].created_at` | datetime | 生成时间。 |
    | `items[].size_bytes` | integer | 文件大小（字节），若可用。 |
    | `items[].tags` | array[string/object] | 已绑定的标签。 |

  - **响应示例：**
    ```json
    {
      "items": [
        {
          "id": "ckpt_001",
          "name": "第 2000 步检查点",
          "type": "checkpoint",
          "path": "s3://artifacts/proj_xxx/run_001/ckpt_001.pt",
          "created_at": "2024-01-02T11:45:00Z",
          "size_bytes": 123456789,
          "tags": []
        },
        {
          "id": "log_tensorboard",
          "name": "TensorBoard 日志",
          "type": "event",
          "path": "s3://artifacts/proj_xxx/run_001/tensorboard",
          "created_at": "2024-01-02T11:50:00Z",
          "tags": []
        }
      ]
    }
    ```
- **curl 示例：**
  ```bash
  curl "http://localhost:8000/projects/proj_xxx/runs/run_001/artifacts"
  ```

### 恢复运行
- **方法与路径：** `POST /projects/{project_id}/runs/{run_id}/resume`
- **功能描述：** 从已有检查点恢复或继续训练（需求 5.2.8）。
- **入参：**
  - **路径参数：**

    | 名称 | 类型 | 必填 | 说明 |
    | --- | --- | --- | --- |
    | `project_id` | string | 是 | 原运行所属项目 ID。 |
    | `run_id` | string | 是 | 原运行 ID。 |

  - **查询参数：**

    | 名称 | 类型 | 必填 | 说明 |
    | --- | --- | --- | --- |
    | `source_artifact_id` | string | 是 | 要恢复的检查点工件 ID。 |

  - **请求体（JSON）：** 与 [创建训练运行](#创建训练运行) 相同，允许覆盖运行名称、模型、超参数与资源配置。

- **出参：** `201 Created`
  - **响应体字段：** 同创建运行，另增加：

    | 字段 | 类型 | 说明 |
    | --- | --- | --- |
    | `resumed_from` | string | 指明使用的源检查点 ID。 |

  - **响应示例：**
    ```json
    {
      "id": "run_002",
      "project_id": "proj_xxx",
      "name": "run-002",
      "status": "运行中",
      "resumed_from": "ckpt_001",
      "progress": 0.05,
      "started_at": "2024-01-03T08:00:00Z",
      "artifacts": []
    }
    ```
- **curl 示例：**
  ```bash
  curl -X POST "http://localhost:8000/projects/proj_xxx/runs/run_001/resume?source_artifact_id=ckpt_001" \
    -H "Content-Type: application/json" \
    -d '{
          "name": "run-002",
          "model": "llama-2-13b",
          "dataset": "中文科技论文语料",
          "hyperparameters": {
            "learning_rate": 1.5e-5
          }
        }'
  ```

### 为工件打标签
- **方法与路径：** `POST /projects/{project_id}/runs/{run_id}/artifacts/{artifact_id}/tag`
- **功能描述：** 将检查点标记为候选基线模型或发布版本（需求 5.2.9）。
- **入参：**
  - **路径参数：**

    | 名称 | 类型 | 必填 | 说明 |
    | --- | --- | --- | --- |
    | `project_id` | string | 是 | 所属项目 ID。 |
    | `run_id` | string | 是 | 运行 ID。 |
    | `artifact_id` | string | 是 | 工件 ID，例如 `ckpt_001`。 |

  - **请求体（JSON）：**

    | 字段 | 类型 | 必填 | 说明 |
    | --- | --- | --- | --- |
    | `tag` | string | 是 | 标签值，可选：`候选`、`发布`、`归档`。 |
    | `notes` | string | 否 | 备注信息，记录打标签原因。 |

  - **示例请求体：**
    ```json
    {
      "tag": "发布",
      "notes": "在验证集上 BLEU 32.5，通过复核"
    }
    ```
- **出参：** `200 OK`
  - **响应体字段：** 返回最新的工件信息及其标签列表。
  - **响应示例：**
    ```json
    {
      "id": "ckpt_001",
      "name": "第 2000 步检查点",
      "type": "checkpoint",
      "path": "s3://artifacts/proj_xxx/run_001/ckpt_001.pt",
      "created_at": "2024-01-02T11:45:00Z",
      "tags": [
        {
          "value": "发布",
          "notes": "在验证集上 BLEU 32.5，通过复核",
          "applied_at": "2024-01-03T09:15:00Z"
        }
      ]
    }
    ```
- **curl 示例：**
  ```bash
  curl -X POST "http://localhost:8000/projects/proj_xxx/runs/run_001/artifacts/ckpt_001/tag" \
    -H "Content-Type: application/json" \
    -d '{"tag": "发布", "notes": "在验证集上 BLEU 32.5，通过复核"}'
  ```

## 内存存储行为
示例存储层刻意保持简单：
- ID 使用简短前缀自动生成（如 `proj_`、`run_`、`ckpt_`）。
- 运行会自动生成模拟的指标、日志和工件。
- 取消运行会将状态改为 `已取消` 并产生一个最终检查点。
- 恢复运行会克隆原运行的配置并关联到源检查点。

在生产环境中，请将 `app/storage.py` 替换为与你的数据库、作业调度、监控与工件系统相连接的实现。

## 开发提示
- 使用 `app/models.py` 中的 Pydantic 模型作为客户端/服务端通信契约。
- 可以扩展 `InMemoryStorage`，或将其替换为持久化存储以满足真实部署需求。
- 按需增加认证、鉴权和多租户隔离能力。
- 考虑增加后台任务或 Celery 等框架以支持更长耗时的训练编排。
