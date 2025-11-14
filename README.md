# LLM 训练管理 API

一个基于 FastAPI 的轻量级服务，用于集中式管理大语言模型训练项目、数据集、训练配置与部署生命周期。平台将常用管理能力抽象为 RESTful 接口，方便自建训练编排系统或前端面板快速接入。

## 功能概览
- **项目与运行管理**：创建项目、触发训练运行、追踪状态、指标与产出工件。
- **数据集生命周期**：登记数据集元信息、上传小文件样本、查询上传进度。
- **训练配置管理**：上传/删除 YAML 训练配置文件，配合项目引用。
- **部署协作**：为推理服务的启停与健康检查预留 API，便于一体化运维。
- **日志留痕**：所有关键操作均通过 `src/storage` 记录，方便审计与排障。

## 目录结构
```
llm_train_api/
├─ app/                     # FastAPI 应用工厂、依赖与运行时配置
│  ├─ api/                  # 顶层路由注册（聚合 src/features 下的模块）
│  ├─ config.py             # 平台级常量、路径、配额
│  ├─ deps.py               # 依赖注入（数据库/存储句柄）
│  └─ logging.py            # 日志初始化
├─ src/
│  ├─ features/             # 业务域路由实现（datasets、projects、deployments 等）
│  ├─ models/               # Pydantic 请求/响应模型
│  ├─ storage/              # SQLite/JSON 文件存储实现
│  ├─ utils/                # 文件系统与容器执行辅助
│  └─ ...
├─ tests/                   # Pytest 覆盖核心 API 行为
├─ main.py                  # 兼容入口：`uvicorn main:app`
├─ requirements.txt
└─ README.md
```

## 快速开始
1. 安装依赖：`pip install -r requirements.txt`
2. 启动服务：`uvicorn main:app --reload`
3. 打开 `http://localhost:8000/docs` 使用交互式 OpenAPI 文档。

> **提示**：训练运行会调用 `run_train_full_sft.sh`，并假设训练数据与配置位于 `app.config.HOST_TRAINING_PATH` 中。部署时请根据实际路径与脚本调整 `app/config.py`。

## 常用 API 速览
| 资源 | 方法 & 路径 | 说明 |
|------|-------------|------|
| 数据集 | `POST /v1/datasets` | 创建数据集元数据记录 |
| 数据集文件 | `PUT /v1/datasets/{dataset_id}/files` | 上传小文件样本（≤ `MAX_SMALL_FILE_BYTES`） |
| 训练配置 | `PUT /v1/train-config` | 上传训练 YAML（≤ `MAX_YAML_BYTES`） |
| 项目 | `POST /projects` | 注册训练项目并关联数据集/配置 |
| 运行 | `POST /projects/{id or name}/runs` | 校验资源并触发一次训练 |
| 工件 | `GET /projects/{id}/runs/{run_id}/artifacts` | 查询运行产出的文件记录 |
| 日志 | `GET /projects/{id}/runs/{run_id}/logs` | 分页获取运行日志 |

## 训练任务类型与数据规范
平台使用统一的数据集管理与训练配置机制，不同训练范式通过约定输入/输出格式来区分。以下规范可直接作为上传数据的模版：

### 1. Supervised Fine-Tuning (SFT)
- **数据文件格式**：推荐 `JSONL`，每行一个对话样本。
  ```jsonl
  {"conversation_id": "demo-001", "messages": [{"role": "user", "content": "指令"}, {"role": "assistant", "content": "回答"}], "task_tags": ["qa"], "metadata": {"language": "zh"}}
  {"conversation_id": "demo-002", "messages": [{"role": "user", "content": "请总结"}, {"role": "assistant", "content": "总结内容"}]}
  ```
  - `messages` 按顺序排列，至少包含用户与助手两轮。
  - 可选字段：`system_prompt`、`input_template`、`metadata`。
- **训练配置关键字段（YAML）**：
  ```yaml
  task_type: sft
  model_name: qwen-7b
  dataset: datasets/sft_dataset.jsonl
  max_seq_length: 2048
  per_device_train_batch_size: 4
  learning_rate: 2e-5
  num_train_epochs: 3
  ```
  - `task_type` 必须为 `sft`，用于运行脚本识别。
  - `dataset` 字段需与项目登记的 `dataset_name` 对应。
- **训练输出**：
  - 日志指标：`train/loss`、`eval/loss`、`eval/rougeL` 等 JSON 格式指标追加至 `Run.metrics`。
  - 工件：完整模型权重（如 `model_final/` 目录）与 tokenizer 配置包。

### 2. 强化学习（RL，包括 RLHF）
- **数据文件格式**：`JSONL`，支持奖励对齐或偏好对比两种样式。
  ```jsonl
  {"prompt": "请写一首短诗", "chosen": "春风拂面...", "rejected": "我不知道", "metadata": {"source": "beta-feedback"}}
  {"prompt": "翻译：Hello", "responses": [{"content": "你好", "score": 0.9}, {"content": "您好", "score": 0.7}]}
  ```
  - 若提供 `chosen`/`rejected` 字段则默认用于偏好学习；若提供 `responses` 列表则读取最高 `score` 作为正样本。
- **训练配置关键字段**：
  ```yaml
  task_type: rl
  algorithm: ppo
  policy_model: qwen-7b-sft
  reward_model: qwen-7b-rm
  dataset: datasets/rl_preference.jsonl
  rollout_batch_size: 16
  update_epochs: 4
  kl_target: 0.1
  ```
  - `policy_model` 指向已完成 SFT 的权重。
  - `reward_model` 为独立推理服务或本地检查点路径。
- **训练输出**：
  - 日志指标：`reward/mean`, `kl_divergence`, `episode_length`。
  - 工件：强化学习后的策略模型目录，以及可选的奖励模型 checkpoint（如有微调）。

### 3. LoRA 微调
- **数据文件格式**：复用 SFT 的对话 JSONL，支持额外 LoRA 标签。
  ```jsonl
  {"conversation_id": "lora-001", "messages": [{"role": "user", "content": "写一封感谢信"}, {"role": "assistant", "content": "亲爱的团队..."}], "target_modules": ["q_proj", "v_proj"], "rank": 8}
  ```
  - `target_modules` 与 `rank` 可覆盖 YAML 中的默认值，用于样本级别实验。
- **训练配置关键字段**：
  ```yaml
  task_type: lora
  base_model: llama2-7b
  dataset: datasets/lora_demo.jsonl
  lora_r: 8
  lora_alpha: 16
  lora_dropout: 0.05
  train_batch_size: 64
  gradient_accumulation_steps: 4
  use_8bit: true
  ```
  - `base_model` 为原始全量模型；LoRA 权重会在此基础上保存增量。
  - 可选字段：`peft_target_modules`、`bnb_4bit_quant_type` 等。
- **训练输出**：
  - 工件：LoRA 适配器（如 `adapter_config.json`、`adapter_model.safetensors`）。
  - 日志：训练/验证损失、权重规范化统计。

### 4. 大规模预训练（Pretraining）
- **数据文件格式**：推荐 `JSONL` 或 `.txt`。若使用 JSONL，需提供 `text` 字段。
  ```jsonl
  {"doc_id": "pt-0001", "text": "大模型预训练语料第一段...", "metadata": {"domain": "finance"}}
  {"doc_id": "pt-0002", "text": "第二段语料..."}
  ```
  - 文本需完成清洗（去除控制字符、统一编码为 UTF-8）。
  - 可追加 `metadata` 描述来源与保留策略，用于采样器过滤。
- **训练配置关键字段**：
  ```yaml
  task_type: pretrain
  model_name: llama2-7b
  dataset: datasets/pretrain_corpus.jsonl
  sequence_length: 4096
  global_batch_size: 1024
  learning_rate: 3e-4
  warmup_ratio: 0.01
  tokenizer: configs/tokenizer.model
  ```
  - `sequence_length` 决定拼接时的最大 token 长度。
  - `global_batch_size` = `per_device_batch_size × 数据并行度`。
- **训练输出**：
  - 工件：分阶段 checkpoint（如 `step-10000/`），词表或 tokenizer 同步副本。
  - 日志：吞吐量（tokens/sec）、loss 曲线、梯度裁剪统计。

### 上传与引用流程小结
1. 通过 `/v1/datasets` 创建数据集记录并获取 `dataset_id`。
2. 使用 `/v1/datasets/{dataset_id}/files` 上传规范化数据文件。
3. 通过 `/v1/train-config` 上传包含 `task_type` 与路径字段的 YAML。
4. 调用 `/projects` 注册项目，字段 `dataset_name` 与 `training_yaml_name` 分别对应已上传文件的相对路径。
5. 调用 `/projects/{id}/runs` 触发训练，系统会自动校验文件存在并执行脚本。

## 测试
```bash
pytest
```

更多实现细节请阅读 `src/features` 下各模块与 `tests/` 中的用例。
