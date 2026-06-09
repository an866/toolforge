# ToolForge — 项目状态与交接文档

> **最后更新:** 2026-06-06  
> **分支:** master  
> **远程:** https://github.com/an866/toolforge.git  
> **状态:** Phase 1 实施完成，79 测试通过，待手动测试验证

---

## 一、项目概述

ToolForge 是一个自进化工具 AI Agent 框架。核心突破：Agent 在执行任务时自主感知工具缺失，实时生成代码创造新工具，通过 Docker 安全沙盒验证后入库，使工具库持续进化。

### Phase 1 目标（已完成）

跑通核心闭环：**感知缺失 → 生成工具 → 沙盒验证 → 入库 → 复用**

---

## 二、当前项目结构

```
D:\ClaudeAI\project_2\
├── STATUS.md                          # 本文件
├── pyproject.toml                     # 项目配置 + 依赖 + CLI entry point
├── config.yaml                        # 运行时配置（API key 用 ${DEEPSEEK_API_KEY}）
├── .gitignore
├── sandbox/
│   └── Dockerfile                     # 沙盒镜像定义（python:3.12-slim + 常用库）
├── docs/
│   └── superpowers/
│       ├── specs/
│       │   └── 2026-05-31-toolforge-design.md    # 设计规范
│       └── plans/
│           └── 2026-05-31-toolforge-phase-1.md   # 实施计划（20任务）
├── toolforge/
│   ├── __init__.py                    # __version__ = "0.1.0"
│   ├── config.py                      # Pydantic Settings 配置管理（5个子配置类）
│   ├── exceptions.py                  # 自定义异常层级（8个异常类）
│   ├── py.typed                       # PEP 561 类型标记
│   ├── cli.py                         # CLI 入口（toolforge 命令）
│   ├── llm/
│   │   ├── base.py                    # LLMAdapter 抽象接口
│   │   └── deepseek.py               # DeepSeek V4 Pro 适配器
│   ├── registry/
│   │   ├── models.py                  # ToolMeta, ToolRecord, ExecutionRecord 等
│   │   ├── file_store.py              # 文件系统存储层（原子写入）
│   │   ├── db_store.py                # SQLite 管理层（FK/索引/rollback）
│   │   ├── vector_store.py            # ChromaDB 向量语义检索
│   │   └── registry.py               # 统一接口（三层协调 + 信任链排序）
│   ├── sandbox/
│   │   ├── docker_manager.py          # Docker 容器管理（安全配置 + 容器防泄漏）
│   │   ├── image_builder.py           # 镜像构建器
│   │   └── test_runner.py            # 容器内测试执行器（预留）
│   ├── smith/
│   │   ├── models.py                  # GeneratedTool, StaticCheckResult
│   │   ├── static_checker.py          # AST 静态安全检查（FORBIDDEN_IMPORTS/CALLS）
│   │   ├── template_engine.py         # 模板匹配与渲染
│   │   ├── code_generator.py          # LLM 自由生成工具代码
│   │   └── smith.py                  # 统一接口（模板→生成→检查→验证流水线）
│   ├── master/
│   │   ├── planner.py                 # LLM 任务分解（2-6步骤）
│   │   ├── tool_sensor.py             # 双重触发工具缺失感知
│   │   └── agent.py                  # Master Agent 主循环（ReAct 编排）
│   ├── templates/                     # 8 个预置工具模板
│   │   ├── api_caller/               # HTTP API 调用
│   │   ├── file_parser/              # 文件解析（JSON/CSV/XML）
│   │   ├── text_processor/           # 文本处理（正则）
│   │   ├── data_transformer/         # 数据转换
│   │   ├── data_extractor/           # 数据提取
│   │   ├── format_converter/         # 格式转换
│   │   ├── calculator/              # 数学计算
│   │   └── system_command/          # 系统操作
│   └── tools/
│       └── builtin/
│           ├── file_reader/           # 读取文件内容
│           └── echo/                  # 回显消息
└── tests/
    ├── conftest.py                    # 共享 fixtures（temp_dir, sample_config）
    ├── test_llm/
    │   └── test_deepseek.py          # 6 tests
    ├── test_registry/
    │   ├── test_file_store.py        # 5 tests
    │   ├── test_db_store.py          # 8 tests
    │   ├── test_vector_store.py      # 4 tests
    │   └── test_registry.py          # 4 tests
    ├── test_sandbox/
    │   └── test_docker_manager.py    # 4 tests
    ├── test_smith/
    │   ├── test_static_checker.py    # 9 tests
    │   ├── test_template_engine.py   # 4 tests
    │   ├── test_code_generator.py    # 3 tests
    │   └── test_smith.py            # 3 tests
    ├── test_master/
    │   ├── test_planner.py           # 2 tests
    │   ├── test_tool_sensor.py       # 3 tests
    │   └── test_agent.py            # 3 tests
    ├── test_integration/
    │   └── test_full_loop.py         # 3 tests
    └── test_security/
        └── test_malicious_code.py    # 14 tests (12 malicious payloads)
```

---

## 三、架构总览

```
用户 / CLI
    │
    ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Master      │────▶│  Tool Smith   │────▶│  Sandbox     │
│  Agent       │     │  (子Agent)     │     │  (Docker)    │
│  编排/感知    │     │  模板+生成     │     │  验证/测试    │
└──────┬───────┘     └──────────────┘     └──────┬───────┘
       │                                        │
       └──────────  Tool Registry ◀─────────────┘
                   (文件+SQLite+向量)
```

### 安全三层防护

| 层级 | 组件 | 防护 |
|------|------|------|
| L0 主机 | Master Agent, Tool Smith | 生成代码绝不直接执行 |
| L1 沙盒 | Docker 容器 | read-only, --network=none, cap-drop=ALL, no-new-privileges, pids-limit=50, memory=256m, timeout=30s |
| L2 注册表 | Tool Registry | 来源分级（builtin > verified > auto），异常检测自动标记 suspicious |

---

## 四、完整数据流

```
用户任务
  → Master Agent (Planner 分解步骤)
    → Tool Registry (向量语义检索)
    → 无匹配 → ToolSensor 双重触发感知缺失
              → Tool Smith (模板匹配 / LLM生成 + AST静态检查)
              → Sandbox (Docker 隔离验证)
              → Tool Registry (三层入库)
    → Master Agent (调用工具，Sandbox 执行)
    → 返回结果
```

---

## 五、Git 提交历史（25 commits）

```
92940d5 fix: critical fixes - sandbox image, vector close, LLM validation, tool invocation
4f42666 test: add end-to-end integration tests and security tests
cabdc4c feat: add CLI entry point, built-in tools, and 8 pre-built templates
3d3edee feat: add Master Agent with ReAct loop, tool sensor, and planner
fc3fa98 feat: add task planner that decomposes user tasks into executable steps
8d8114e feat: add ToolSmith unified interface with template→generate→check→verify pipeline
20f4c4a feat: add LLM-powered code generator for tool creation
c905594 feat: add template engine for matching and rendering tool templates
714d3f9 feat: add AST-based static security checker for generated tools
1dcf15b feat: add Docker sandbox image builder with pre-installed dependencies
bcda3b9 fix: prevent container leak with auto_remove + finally cleanup, remove duplicate config
c8c6c8d feat: add Docker sandbox manager with secure container execution
11276f5 fix: persist ToolRecord.id across file save/load cycles
6f55b89 feat: add unified Tool Registry interface coordinating three storage layers
772c1b6 feat: add ChromaDB vector store for semantic tool search
6dde0c3 fix: FK enforcement, indexes, rollback, updated_at, and extra tests for DBStore
dfec9fb feat: add SQLite-based DB store for tool metadata and execution tracking
f40301a fix: atomic save, error handling, delete returns bool in FileStore
f4e476b feat: add Tool Registry models and file store layer
a916025 fix: address LLM adapter review - retry logic, fence stripping, error handling
0c84c5a feat: add LLM adapter layer with DeepSeek support
2fbd13e fix: address code review issues - thread safety, error handling, env var expansion
dc90c4d chore: project scaffold with config, exceptions, and dependencies
a1dd6bf docs: add comprehensive Phase 1 implementation plan with 20 tasks
01b98b1 docs: ToolForge Phase 1 设计规范
```

---

## 六、测试结果

```
79 passed, 5 warnings in 3.71s
```

| 测试模块 | 数量 | 覆盖 |
|----------|:----:|------|
| LLM Adapter | 6 | 初始化、API调用、结构化输出、工厂函数、fence stripping |
| File Store | 5 | save/load、不存在、列表、删除、ID保留 |
| DB Store | 8 | 建表、插入/查询、分类搜索、执行日志、统计、状态更新 |
| Vector Store | 4 | add/search、删除、空结果、count |
| Registry | 4 | 增+搜、空搜索、执行统计、可疑标记 |
| Sandbox | 4 | 安全配置、Docker可用/不可用、镜像构建状态 |
| Static Checker | 9 | 安全代码、8种拦截模式 + 白名单 |
| Template Engine | 4 | 加载、匹配、无匹配、渲染 |
| Code Generator | 3 | 生成工具、来源标记、安全prompt |
| Tool Smith | 3 | 模板路径、LLM路径、静态检查拦截 |
| Planner | 2 | 任务分解、结构化步骤 |
| Tool Sensor | 3 | 缺失检测、已有工具、失败评估 |
| Master Agent | 3 | 完成任务、发明工具、发明限制 |
| Integration | 3 | 完整闭环、已有工具复用、生成失败 |
| Security | 14 | 12种恶意代码拦截 + 安全代码通过 + 语法错误 |

---

## 七、待完成事项

### ⚠️ 需要你手动操作

**1. 启动 Docker Desktop** 并确认 `docker ps` 正常工作

**2. 设置环境变量并安装项目：**

```powershell
cd D:\ClaudeAI\project_2
set DEEPSEEK_API_KEY=sk-你的DeepSeek_API_Key
pip install -e ".[dev]"
```

**3. 运行全部测试确认环境正常：**

```powershell
pytest tests/ -v
```

预期：**79 passed**

**4. 构建沙盒 Docker 镜像：**

```powershell
python -c "from toolforge.sandbox.image_builder import ImageBuilder; ImageBuilder().build(force=True)"
```

**5. 运行真实任务测试：**

```powershell
python -m toolforge.cli "读取config.yaml文件，提取所有配置key名称"
```

预期：Agent 分解任务 → 检索/发明工具 → Docker 沙盒执行 → 返回结果清单

---

## 八、已知限制（Phase 2 解决）

1. **ReAct 循环未完全闭环** — 当前实现按步骤顺序执行，未根据工具输出动态调整后续步骤（`evaluate_failure` 方法已就绪但未接入主循环）
2. **仅支持 DeepSeek API** — 适配器接口已抽象，添加 OpenAI/Claude 只需新增适配器类
3. **模板匹配为关键词而非语义** — TemplateEngine 用 token 匹配而非 embedding，已安装 ChromaDB 可扩展
4. **工具调用模式未验证** — execute() 已添加 tool_args 参数支持实际调用，但 MasterAgent 未使用此功能
5. **config.yaml 全局单例** — 多线程安全已用 Lock 保护，但不支持配置热重载
6. **无日志系统** — 使用 print() 而非结构化日志
7. **SecurityConfig 部分字段未接入** — `rate_limit_per_tool` 和 `human_approval_mode` 已定义但未执行

---

## 九、后续路线图

### Phase 2（预计 Tasks 20→30）：多 API 适配 + 核心增强
- OpenAI、Anthropic 适配器
- LLM embedding 替代 ChromaDB 默认模型
- 真正的 ReAct 循环（观察→调整→重试）
- 工具实际调用链路打通
- 结构化日志
- 安全配置完整接入

### Phase 3（预计 Tasks 30→40）：Web 面板 + 协作
- Web 管理面板（FastAPI + 前端）
- 工具版本管理
- 工具分享/导出
- 多任务并发执行

---

## 十、新对话快速启动

下次打开 Claude Code，在项目目录 `D:\ClaudeAI\project_2` 下说：

```
请阅读 STATUS.md 了解项目当前状态，然后帮我继续开发。
```

关键文件速查：
- 设计规范：`docs/superpowers/specs/2026-05-31-toolforge-design.md`
- 实施计划：`docs/superpowers/plans/2026-05-31-toolforge-phase-1.md`
- 配置：`config.yaml` + `toolforge/config.py`
- CLI 入口：`toolforge/cli.py`
