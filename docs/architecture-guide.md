# ToolForge — 架构指南

> 面向开发者。介绍模块协作、数据流、以及如何扩展框架。

## 一、总览

```
用户任务 (CLI)
    │
    ▼
┌──────────────────────────────────────────────────┐
│                  Master Agent                     │
│  ┌──────────┐  ┌───────────┐  ┌───────────────┐  │
│  │ Planner  │  │ToolSensor │  │ ReAct Loop    │  │
│  │ 任务分解  │  │ 缺失感知   │  │ 编排 & 决策    │  │
│  └──────────┘  └───────────┘  └───────────────┘  │
└──┬──────────────┬────────────────┬──────────────┘
   │              │                │
   ▼              ▼                ▼
┌──────────┐ ┌──────────┐  ┌──────────────┐
│Tool Smith│ │ Sandbox  │  │Tool Registry │
│工具发明   │ │ Docker   │  │  工具库       │
│工厂      │ │ 安全执行  │  │ 三层存储      │
└────┬─────┘ └────┬─────┘  └──────┬───────┘
     │            │               │
     └────────────┴───────────────┘
          生成 → 验证 → 入库
```

## 二、模块职责

### 2.1 Master Agent (`toolforge/master/`)

协调整个执行流程。内部包含三个子组件：

| 组件 | 文件 | 职责 |
|------|------|------|
| **Planner** | `planner.py` | 用 LLM 将用户任务拆成 2-6 个可执行步骤 |
| **ToolSensor** | `tool_sensor.py` | 双重触发感知工具缺失 |
| **MasterAgent** | `agent.py` | ReAct 主循环，编排搜索→发明→执行→记录 |

**执行流程：**

```
用户任务
  → Planner.plan(task) → steps[]
    → for each step:
      → Registry.search(capability)
      → 无匹配 → ToolSensor.detect() → 判定缺失
        → ToolSmith.invent_tool() → 生成+验证+入库
      → Sandbox.execute(tool_code, test_code)
      → Registry.log_execution()
  → TaskResult
```

### 2.2 Tool Smith (`toolforge/smith/`)

工具发明工厂，提供两条路径：

| 路径 | 组件 | 触发条件 |
|------|------|------|
| **模板匹配** | `template_engine.py` | 任务能力描述与预置模板匹配 |
| **LLM 自由生成** | `code_generator.py` | 无模板匹配时 |

两条路径都经过相同的安全流水线：

```
模板匹配 / LLM生成
  → StaticChecker.check()     # L1: AST 静态分析
  → Sandbox.execute()         # L2: Docker 隔离执行
  → Registry.add_tool()       # L3: 入库
```

**关键接口：**

```python
# smith.py
class ToolSmith:
    async def invent_tool(
        self, name: str, purpose: str, context: str
    ) -> InventionResult:
        """模板匹配 → LLM生成 → 静态检查 → 沙盒验证"""
```

### 2.3 Sandbox (`toolforge/sandbox/`)

Docker 容器安全执行环境。

| 组件 | 文件 | 职责 |
|------|------|------|
| **DockerManager** | `docker_manager.py` | 容器创建、执行、销毁 |
| **ImageBuilder** | `image_builder.py` | 构建预装依赖的沙盒镜像 |

**安全配置（容器级别）：**

| 参数 | 值 | 目的 |
|------|------|------|
| `read_only` | True | 禁止写入文件系统 |
| `network_mode` | `none` | 禁止网络访问 |
| `cap_drop` | `ALL` | 剥夺所有 Linux capabilities |
| `security_opt` | `no-new-privileges` | 禁止提权 |
| `mem_limit` | 256m | 限制内存 |
| `pids_limit` | 50 | 限制进程数 |
| `tmpfs` | `/tmp: size=64m,noexec` | 临时空间禁止执行 |

**执行流程：**

```
1. 将 tool.py + test_tool.py 写入临时目录
2. docker run (detach, 挂载 ro volume)
3. 等待容器完成 (asyncio.wait_for timeout)
4. 解析 __RESULT__ 标记获取测试结果
5. finally: container.remove(force=True)
```

### 2.4 Tool Registry (`toolforge/registry/`)

三层存储架构，各司其职：

| 层 | 存储 | 用途 |
|------|------|------|
| **FileStore** | 文件系统 (JSON) | 工具代码持久化 |
| **DBStore** | SQLite | 结构化元数据、执行日志、统计 |
| **VectorStore** | ChromaDB | 语义向量检索 |

**统一接口 (`registry.py`)：**

```python
class ToolRegistry:
    async def search(query, top_k=3) -> list[ToolRecord]
    async def add_tool(record: ToolRecord)
    async def log_execution(tool_id, task_id, success, ...)
    async def mark_suspicious(tool_id)
    async def get_stats(tool_id) -> ExecutionStats
```

**工具来源信任链（排序优先级）：**

```
builtin > verified > auto
```

### 2.5 LLM Adapter (`toolforge/llm/`)

抽象接口，支持多 Provider：

```python
# base.py
class LLMAdapter(ABC):
    async def chat(messages) -> str
    async def generate_structured(system_prompt, user_prompt, output_schema) -> dict

# deepseek.py — Phase 1 唯一实现
class DeepSeekAdapter(LLMAdapter): ...
```

工厂函数 `create_adapter(provider, model, api_key, ...)` 根据 provider 名称返回对应实例。

## 三、完整数据流

```
用户: "读取 config.yaml 并列出所有 key"
    │
    ▼
[CLI: cli.py]
    ├── 加载 config.yaml → Config
    ├── 初始化 DockerManager, ImageBuilder, Adapter, Registry
    ├── 初始化 TemplateEngine, StaticChecker, CodeGenerator → ToolSmith
    ├── 初始化 Planner, ToolSensor → MasterAgent
    │
    ▼
[MasterAgent.run(task)]
    │
    ├── [1] Planner.plan("读取 config.yaml...")
    │       └── LLM → [{description: "读取文件", capability: "file_reader", ...},
    │                   {description: "提取key", capability: "text_extractor", ...}]
    │
    ├── [2] for each step:
    │   │
    │   ├── Registry.search("file_reader")
    │   │   ├── FileStore: 无
    │   │   ├── DBStore: 无
    │   │   └── VectorStore: 无 → 返回 []
    │   │
    │   ├── ToolSensor.detect("file_reader")
    │   │   └── LLM → MissingToolRequest(is_missing=True, tool_name="file_reader")
    │   │
    │   ├── ToolSmith.invent_tool("file_reader", ...)
    │   │   ├── TemplateEngine.match("file_reader")
    │   │   │   └── 遍历模板 YAML → 关键词匹配 → 返回 [file_parser] 或 []
    │   │   ├── 有匹配 → render(template, params)
    │   │   ├── 无匹配 → CodeGenerator.generate()
    │   │   │   └── LLM → GeneratedTool(code="...", test_code="...")
    │   │   ├── StaticChecker.check(code)
    │   │   │   └── AST walk → 检查 imports/calls → passed/violations
    │   │   ├── Sandbox.execute(code, test_code)
    │   │   │   └── Docker run → container.wait → parse __RESULT__
    │   │   └── 返回 InventionResult
    │   │
    │   ├── Registry.add_tool(record)
    │   │   ├── FileStore.save() → tool_registry/file_reader.json
    │   │   ├── DBStore.insert() → toolforge.db
    │   │   └── VectorStore.add() → chromadb
    │   │
    │   ├── Sandbox.execute(tool.code, tool.test_code)
    │   │   └── 实际调用工具，获取结果
    │   │
    │   └── Registry.log_execution(...)
    │
    └── [3] 返回 TaskResult
```

## 四、如何添加新内容

### 4.1 添加新 LLM Provider

```python
# toolforge/llm/openai.py
from toolforge.llm.base import LLMAdapter

class OpenAIAdapter(LLMAdapter):
    def __init__(self, model, api_key, base_url=None, timeout=60):
        ...
    
    async def chat(self, messages):
        ...
    
    async def generate_structured(self, system_prompt, user_prompt, output_schema):
        ...

# toolforge/llm/base.py — 在 create_adapter 中添加
def create_adapter(provider, ...):
    if provider == "openai":
        from toolforge.llm.openai import OpenAIAdapter
        return OpenAIAdapter(...)
```

### 4.2 添加新工具模板

```
toolforge/templates/my_tool/
├── template.yaml      # 元数据定义
├── tool_template.py   # 工具代码骨架（{{ param }} 占位）
└── test_template.py   # 测试代码骨架
```

`template.yaml` 格式：

```yaml
name: my_tool
description: "简短描述工具功能"          # ← 用户查询匹配的关键字段
category: my_category
parameters:
  - name: param_name
    type: string
    required: true
    description: "参数说明"
whitelist:                              # 静态检查白名单
  - re                                  # 允许 import re
```

模板代码用 `{{ param_name }}` 做占位符，TemplateEngine 渲染时替换。

### 4.3 添加新模块

遵循以下模式：

1. **新建包** `toolforge/my_module/`，包含 `__init__.py`
2. **定义接口** — 抽象基类或 dataclass 模型
3. **接入 CLI** — 在 `cli.py` 中初始化和注入
4. **添加配置** — 在 `config.py` 中添加对应 Pydantic Settings 类，`config.yaml` 中加对应段
5. **写测试** — 在 `tests/test_my_module/` 下添加

## 五、错误处理架构

```
ToolForgeError (base)
├── ConfigError
├── LLMError
│   └── LLMAuthenticationError
├── ToolGenerationError
├── StaticCheckError
├── SandboxError
│   └── SandboxTimeoutError
└── RegistryError
```

**异常传播路径：**

```
ToolSmith.invent_tool() 失败
  → StaticCheckError / ToolGenerationError / SandboxError
    → MasterAgent.run() catch at step level
      → TaskResult(success=False, error="...")
        → CLI: print error + sys.exit(1)
```

## 六、配置系统

`config.yaml` → Pydantic Settings → 运行时配置对象。

```
Config
├── LLMConfig       (provider, model, api_key, base_url, timeout, max_retries)
├── SandboxConfig   (memory_limit_mb, cpu_limit, timeout_seconds, pids_limit, base_image)
├── SmithConfig     (template_match_threshold, max_fix_attempts)
├── RegistryConfig  (db_path, vector_path, tools_path)
└── SecurityConfig  (human_approval_mode, max_inventions_per_task, rate_limit_per_tool)
```

环境变量引用：`${DEEPSEEK_API_KEY}` 在加载时自动展开。

## 七、关键设计决策

| 决策 | 原因 |
|------|------|
| 生成代码绝不直接在主机执行 | 安全 L0 层隔离 |
| 测试代码静态检查降级为 Warning | 测试代码已在 Docker 沙盒中执行，双重检查无必要 |
| 模板匹配用关键词而非 embedding | Phase 1 快速实现，Phase 2 可升级为语义匹配 |
| Docker 容器 detach + wait + finally remove | 防止容器泄漏 |
| FileStore + DBStore + VectorStore 三层 | 代码/元数据/语义检索各用最优存储 |
