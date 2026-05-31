# ToolForge — 自进化工具 AI Agent 框架

## 概述

ToolForge 是一个能够自主发明、测试、入库并复用工具的 AI Agent 框架。常规 Agent 受限于预设固定工具集，面对长尾任务时往往无能为力。ToolForge 的核心突破在于：让 Agent 在执行任务时自主感知工具缺失，实时生成代码创造新工具，并通过安全沙盒验证后入库，使工具库持续进化。

**Phase 1 目标**：跑通核心闭环 — 感知缺失 → 生成工具 → 沙盒验证 → 入库 → 复用。

## 技术栈

| 层 | 技术 |
|------|------|
| 语言 | Python 3.12+ |
| LLM API | 适配层支持多家 API，Phase 1 使用 DeepSeek V4 Pro |
| 沙盒 | Docker (`docker-py`) |
| 向量检索 | ChromaDB |
| 管理数据库 | SQLite |
| 配置管理 | YAML + Pydantic settings |
| 模板系统 | YAML 模板定义 + Jinja2 渲染 |
| 并行 | `asyncio` |

## 架构总览

```
                        ┌────────────────────┐
                        │   用户 / CLI         │
                        └─────────┬──────────┘
                                  │ 任务输入
                        ┌─────────▼──────────┐
                        │  Master Agent      │
                        │  (编排·感知·决策)   │
                        └───┬──────┬─────┬──┘
                            │      │     │
               ┌────────────┘      │     └────────────┐
               ▼                   ▼                  ▼
        ┌────────────┐    ┌──────────────┐    ┌──────────────┐
        │ Tool Smith  │    │   Sandbox    │    │  Tool        │
        │ (子 Agent)  │    │  (Docker)    │    │  Registry    │
        │ 模板+生成    │    │  验证/测试   │    │ 存储+检索     │
        └──────┬─────┘    └──────────────┘    └──────────────┘
               │                  │
               └──────────────────┘
                 生成 → 验证 → 入库
```

### 安全边界（三层隔离）

| 层级 | 组件 | 风险 | 对策 |
|------|------|------|------|
| **L0 主机层** | Master Agent, Tool Smith, Registry | LLM 生成恶意代码 | 生成代码**绝不**在主机执行，仅存为文本传递 |
| **L1 沙盒层** | Docker 容器 | 容器逃逸、资源耗尽 | 只读 rootfs、`--network=none`、内存/CPU 限制、超时 kill |
| **L2 注册表层** | Tool Registry | 恶意工具通过验证后入库 | 来源标记（auto/verified/builtin）、调用异常检测 |

### 关键安全原则

1. **生成代码零信任**：LLM 生成的代码先存为 `.py` 文件，通过 stdin 管道传入容器，容器内执行结果通过 stdout 返回，代码文件从不直接在主机执行。
2. **最小权限容器**：每个验证容器使用 `--read-only`、`--network=none`、`--tmpfs /tmp`、`--memory=256m`、`--cpus=1`、`--timeout=30s`。
3. **工具来源分级**：入库工具标记来源（`auto` / `verified` / `builtin`），Master Agent 按优先级选择调用。
4. **调用追踪**：每个工具记录调用次数、成功率、最近异常，自动标记可疑工具。

---

## 模块一：Master Agent — 编排核心

### 职责

- 接收用户任务，拆解为可执行步骤
- 维护 ReAct 循环：思考 → 调用工具 → 观察结果 → 继续 / 发现缺失
- 感知工具缺失：当现有工具无法满足当前步骤时，触发工具发明
- 管理工具调用优先级：`verified > builtin > auto`
- 与 Tool Smith 协调，等待新工具生成+验证+入库后继续任务

### 工具缺失感知（双重触发）

**触发路径 1：LLM 主动感知**

Agent 在思考链中分析任务步骤，对比工具库能力，自主判断缺失并请求发明新工具。

**触发路径 2：失败驱动**

调用现有工具后结果不符合预期（乱码、空结果、结构丢失等），Agent 判定工具能力不足，触发发明流程。

### 核心流程

```python
async def run_task(task: str):
    steps = await plan(task)           # LLM 分解任务步骤
    for step in steps:
        while not step.done:
            tool = await registry.search(step.description)
            if tool is None:
                # 触发工具发明
                new_tool = await invent_tool(
                    name=infer_tool_name(step),
                    purpose=step.description,
                    context=step.context
                )
                if new_tool.valid:
                    registry.add(new_tool)
                    tool = new_tool
                else:
                    step.mark_failed("无法生成有效工具")
                    continue

            result = await sandbox.execute(tool, step.params)
            step.observe(result)
```

### Master Agent 安全职责

- 不在主机执行工具代码
- `invent_tool` 请求记录完整日志，支持可配置的"人工确认模式"
- 同一工具短时间大量调用时自动暂停并告警

---

## 模块二：Tool Smith — 工具工厂

### 职责

将 Master Agent 的工具缺失请求转化为可运行的 Python 代码。

### 三层生成流水线

```
invent_tool(name, purpose, context)
        │
        ▼
   ┌─────────────┐
   │ ① 模板匹配   │  向量语义搜索 tool_templates/ 中匹配模板
   └──────┬──────┘
          │ 匹配度 > 阈值？ ── 否 ──┐
          │ 是                      │
          ▼                         ▼
   ┌─────────────┐          ┌──────────────┐
   │ ② 模板填充   │          │ ③ LLM 自由生成 │
   │ LLM 填参数   │          │ 完整代码+文档   │
   │ + 适配逻辑   │          │ + 测试用例      │
   └─────────────┘          └──────────────┘
          │                         │
          └──────────┬──────────────┘
                     ▼
              ┌──────────────┐
              │ 代码静态检查  │  AST 扫描、黑名单、安全检查
              │ (沙盒执行前)  │
              └───────────────┘
                     ▼
                交付给 Sandbox
```

### 模板系统

每个模板为一个目录，包含：
- `template.yaml`：模板定义（名称、类型、参数、描述）
- `tool_template.py`：工具代码骨架，占位符待填充
- `test_template.py`：测试代码骨架

预置 5-8 个高频模板：HTTP 调用、文件解析、文本处理、数据转换、系统命令、数据提取、格式转换、计算类。

### 生成规范

LLM 必须输出结构化内容：

| 字段 | 说明 |
|------|------|
| `tool_name` | 工具名（函数名风格） |
| `version` | 语义版本 |
| `description` | 功能描述 |
| `category` | 分类 |
| `dependencies` | 依赖列表 |
| `code` | 工具实现代码 |
| `test_code` | 测试代码 |
| `usage_example` | 使用示例 |
| `source` | 固定 `"llm_generated"` |

### 静态安全检查（AST 扫描，不执行）

拦截项：
- 危险导入：`os`, `subprocess`, `sys`, `ctypes`, `pickle`
- 危险函数：`eval()`, `exec()`, `compile()`, `__import__()`
- 文件危险操作：`open()`, `os.remove()`, `shutil.rmtree()`
- 网络调用：`requests`, `urllib`, `socket`
- 可疑模式：无限循环、无上限递归

白名单例外：模板声明了需要网络/文件操作的，在模板中标记，LLM 填充时保留但记录安全日志。所有危险调用最终由 Docker 沙盒层兜底限制。

---

## 模块三：Sandbox — Docker 安全验证

### 职责

接收 Tool Smith 生成的代码，在隔离容器中运行并验证正确性和安全性。

### 验证流程

```
Tool Smith 产出
  ├── tool_code.py
  ├── tool_test.py
  └── tool_meta.yaml
        │
        ▼
  ① 构建测试容器镜像（基于 python:3.12-slim + 依赖，首次可缓存）
        ▼
  ② 启动容器（安全配置全开）
        ▼
  ③ stdin 注入代码，执行测试，捕获 stdout/stderr
        ▼
  ④ 收集结果：exit_code, execution_time, resource_usage, stdout, stderr
        ▼
  ⑤ 判定：
     PASS → 提交 Registry
     FAIL（测试不通过）→ 反馈 Tool Smith 修正（上限 2 次）
     FAIL（超时/资源耗尽）→ 丢弃，记录安全日志
```

### Docker 安全配置（完整清单）

```bash
docker run \
  --rm \
  --read-only \
  --network=none \
  --memory=256m \
  --memory-swap=256m \
  --cpus=1 \
  --pids-limit=50 \
  --tmpfs /tmp:size=64m,noexec \
  --cap-drop=ALL \
  --security-opt=no-new-privileges \
  --ulimit nofile=64 \
  --timeout 30 \
  toolforge-sandbox:latest \
  python /tmp/test_runner.py
```

### 反馈策略

| 结果 | 处理 |
|------|------|
| **PASS** | 工具入库，Master Agent 继续任务 |
| **测试不通过** | 错误反馈 Tool Smith，最多 2 次修正尝试 |
| **超时/资源耗尽** | 标记为危险生成，丢弃并记录 |
| **静态检查拦截** | 不进入沙盒，直接拒绝并记录 |

### 预置依赖

基础镜像预装：`requests`, `beautifulsoup4`, `pandas`, `pillow`, `lxml`, `openpyxl`, `python-docx`, `PyPDF2`。

额外依赖走 `pip install` 白名单机制。

---

## 模块四：Tool Registry — 三层存储与检索

### 三层存储架构

| 层 | 技术 | 职责 |
|------|------|------|
| **文件层** | 本地文件系统，按类别/工具名组织 | 代码权威存储、版本管理、人类可读 |
| **SQLite 层** | SQLite | 元数据查询、调用统计、安全审计、模板管理 |
| **向量层** | ChromaDB | 语义检索、模糊匹配、相似工具推荐 |

### 文件目录结构

```
tool_registry/
├── document_processing/
│   ├── pdf_extract_text/
│   │   ├── tool.py
│   │   ├── test_tool.py
│   │   ├── meta.yaml
│   │   └── versions/
│   └── pdf_extract_table/
├── data_fetching/
├── text_processing/
├── data_transformation/
└── system/
```

### SQLite 核心表

**工具目录表 `tools`**：name, description, category, source(builtin/auto/verified), status(active/deprecated/suspicious), dependencies, file_path, meta_path, embedding_id, created_at, updated_at

**调用记录表 `executions`**：tool_id, task_id, success, execution_time_ms, sandbox_id, error_message, created_at

**安全日志表 `security_log`**：tool_id, event_type(static_check_fail/sandbox_fail/marked_suspicious), detail, created_at

### 工具来源信任链

| 来源 | 标签 | 优先度 | 沙盒验证 | 可升级为 |
|------|------|:------:|:------:|:------:|
| 系统内置 | `builtin` | ⭐⭐⭐ | 跳过 | — |
| 人工审核 | `verified` | ⭐⭐ | 已通过 | — |
| LLM 自动生成 | `auto` | ⭐ | 必须通过 | `verified` |
| 可疑标记 | `suspicious` | ❌ | 禁用 | 重新审核后升级 |

### 检索流程

1. 向量检索（ChromaDB）：语义匹配 top-5
2. 精确过滤（SQLite）：按 status=active + source 优先级排序
3. 返回最优工具 + 备选列表（含示例、依赖、成功率）
4. 无结果 → 触发 `invent_tool()`

---

## 项目结构

```
toolforge/
├── cli.py                    # CLI 入口
├── config.py                 # 配置管理（Pydantic settings）
├── master/
│   ├── agent.py              # Master Agent 主循环
│   ├── planner.py            # 任务分解
│   └── tool_sensor.py        # 工具缺失感知
├── smith/
│   ├── smith.py              # Tool Smith 入口
│   ├── template_engine.py    # 模板匹配与填充
│   ├── code_generator.py     # LLM 自由生成
│   └── static_checker.py     # AST 静态安全检查
├── sandbox/
│   ├── sandbox.py            # Docker 沙盒管理
│   ├── image_builder.py      # 镜像构建
│   └── test_runner.py        # 容器内测试执行器（注入容器中使用）
├── registry/
│   ├── registry.py           # Registry 统一接口
│   ├── file_store.py         # 文件存储层
│   ├── db_store.py           # SQLite 管理层
│   └── vector_store.py       # ChromaDB 向量层
├── llm/
│   ├── adapter.py            # LLM 适配接口
│   ├── deepseek.py           # DeepSeek 适配器
│   └── openai_adapter.py     # OpenAI 适配器（预留）
├── templates/                # 预置工具模板
│   ├── api_caller/
│   ├── file_parser/
│   ├── text_processor/
│   ├── data_transformer/
│   ├── system_command/
│   ├── data_extractor/
│   ├── format_converter/
│   └── calculator/
├── tools/                    # 内置工具
│   └── builtin/
│       ├── file_reader/
│       └── echo/
└── tests/
    ├── test_master/
    ├── test_smith/
    ├── test_sandbox/
    └── test_registry/
```

---

## 错误处理

| 场景 | 处理策略 |
|------|------|
| LLM API 调用失败 | 指数退避重试（最多 3 次），失败后告知用户 |
| Docker 不可用 | 启动时检查 Docker daemon，不可用时拒绝启动 |
| 沙盒执行超时 | 30 秒硬超时，容器 kill，工具标记为失败 |
| 工具生成质量低（连续 2 次验证失败） | 放弃该工具，告知 Master Agent 该步骤无法完成 |
| 向量库不可用 | 回退到 SQLite 关键词匹配 |
| 磁盘空间不足 | Registry 写入前检查，拒绝入库并警告 |

---

## 测试策略

| 测试类型 | 覆盖目标 | 工具 |
|------|------|------|
| 单元测试 | 每个模块独立函数 | pytest |
| 集成测试 | 模块间交互（Smith→Sandbox→Registry） | pytest + docker fixtures |
| 安全测试 | 恶意代码注入、容器逃逸尝试、资源耗尽 | 专项用例子集 |
| 端到端测试 | 完整任务执行 + 工具发明 + 复用 | pytest + 真实 Docker |

---

## 配置（config.yaml）

```yaml
llm:
  provider: deepseek           # deepseek | openai | anthropic | custom
  api_key: ${DEEPSEEK_API_KEY}
  model: deepseek-v4-pro
  base_url: https://api.deepseek.com/v1
  max_retries: 3
  timeout: 60

sandbox:
  memory_limit_mb: 256
  cpu_limit: 1
  timeout_seconds: 30
  pids_limit: 50
  base_image: python:3.12-slim

smith:
  template_match_threshold: 0.7
  max_fix_attempts: 2

registry:
  db_path: ./data/toolforge.db
  vector_path: ./data/chromadb
  tools_path: ./tool_registry

security:
  human_approval_mode: false   # true = 新工具入库需人工确认
  max_inventions_per_task: 5   # 单任务最大工具发明数
  rate_limit_per_tool: 50      # 同一工具每分钟最大调用数
```

---

## 数据流全景

```
用户任务
  → Master Agent (编排 + 感知缺失)
    → Tool Registry (语义检索)
    → 无匹配 → Tool Smith (模板/生成 + 静态检查)
              → Sandbox (Docker 验证)
              → Tool Registry (入库)
    → Master Agent (调用工具，Docker 沙盒执行)
    → 结果返回用户
```

---

## 非目标（Phase 1 不做）

- Web 管理面板（Phase 3）
- 工具版本管理与回滚（Phase 3）
- 工具分享/导出（Phase 3）
- 多家 API 完整适配（仅 DeepSeek，Phase 2）
- 分布式沙盒集群
- 工具之间的依赖图推理
