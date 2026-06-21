# ToolForge — 项目状态与交接文档

> **最后更新:** 2026-06-21  
> **分支:** master  
> **远程:** https://github.com/an866/toolforge.git  
> **状态:** Phase 1 手动验证完成，79 测试通过，核心闭环已跑通，修复 5 个 bug

---

## 一、项目概述

ToolForge 是一个自进化工具 AI Agent 框架。核心突破：Agent 在执行任务时自主感知工具缺失，实时生成代码创造新工具，通过 Docker 安全沙盒验证后入库，使工具库持续进化。

### Phase 1 目标（已完成 + 已验证）

跑通核心闭环：**感知缺失 → 生成工具 → 沙盒验证 → 入库 → 复用**

---

## 二、当前项目结构

```
D:\ClaudeAI\project_2\
├── STATUS.md                          # 本文件
├── pyproject.toml                     # 项目配置 + 依赖 + CLI entry point
├── config.yaml                        # 运行时配置
├── .gitignore
├── sandbox/
│   └── Dockerfile                     # 沙盒镜像定义
├── docs/
│   ├── architecture-guide.md          # ★ 新增：架构指南
│   ├── bug-fixes/
│   │   └── 2026-06-21-verification-fixes.md  # ★ 新增：验证修复记录
│   └── superpowers/
│       ├── specs/
│       │   └── 2026-05-31-toolforge-design.md
│       └── plans/
│           └── 2026-05-31-toolforge-phase-1.md
├── toolforge/                         # 主包
├── tests/                             # 79 测试
└── data/                              # 运行时数据（自动生成）
```

### 模块结构

| 模块 | 路径 | 职责 |
|------|------|------|
| CLI | `toolforge/cli.py` | 入口，组装所有组件 |
| Config | `toolforge/config.py` | Pydantic Settings 配置管理 |
| LLM | `toolforge/llm/` | DeepSeek 适配器 + 抽象接口 |
| Registry | `toolforge/registry/` | FileStore + DBStore + VectorStore |
| Sandbox | `toolforge/sandbox/` | Docker 管理 + 镜像构建 |
| Smith | `toolforge/smith/` | 模板引擎 + 代码生成 + 静态检查 |
| Master | `toolforge/master/` | Planner + ToolSensor + Agent |
| Templates | `toolforge/templates/` | 8 个预置工具模板 |
| Built-in Tools | `toolforge/tools/builtin/` | file_reader, echo |

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

详细架构说明见 **[架构指南](docs/architecture-guide.md)**。

### 安全三层防护

| 层级 | 组件 | 防护 |
|------|------|------|
| L0 主机 | Master Agent, Tool Smith | 生成代码绝不直接执行 |
| L1 沙盒 | Docker 容器 | read-only, --network=none, cap-drop=ALL, no-new-privileges, pids-limit=50, memory=256m, timeout=30s |
| L2 注册表 | Tool Registry | 来源分级（builtin > verified > auto），异常检测自动标记 suspicious |

---

## 四、数据流

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

## 五、测试结果 (2026-06-21)

```
79 passed, 5 warnings in 3.41s
Python 3.14.0, Docker SDK 7.1.0, pytest 9.0.3
```

| 测试模块 | 数量 | 覆盖 |
|----------|:----:|------|
| LLM Adapter | 6 | 初始化、API调用、结构化输出、工厂函数 |
| File Store | 5 | save/load、不存在、列表、删除、ID保留 |
| DB Store | 8 | 建表、查询、搜索、日志、统计、状态更新 |
| Vector Store | 4 | add/search、删除、空结果、count |
| Registry | 4 | 增+搜、空搜索、执行统计、可疑标记 |
| Sandbox | 4 | 安全配置、Docker可用/不可用、镜像构建 |
| Static Checker | 9 | 安全代码、8种拦截 + 白名单 |
| Template Engine | 4 | 加载、匹配、无匹配、渲染 |
| Code Generator | 3 | 生成工具、来源标记、安全prompt |
| Tool Smith | 3 | 模板路径、LLM路径、静态检查拦截 |
| Planner | 2 | 任务分解、结构化步骤 |
| Tool Sensor | 3 | 缺失检测、已有工具、失败评估 |
| Master Agent | 3 | 完成任务、发明工具、发明限制 |
| Integration | 3 | 完整闭环、已有工具复用、生成失败 |
| Security | 14 | 12种恶意代码拦截 + 安全代码 + 语法错误 |

---

## 六、手动验证结果 (2026-06-21)

### ✅ 验证通过

| 项目 | 状态 | 备注 |
|------|:----:|------|
| `pip install -e ".[dev]"` | ✅ | 修复 pyproject.toml 后成功 |
| `pytest tests/ -v` | ✅ | 79 passed |
| Docker Desktop | ✅ | `docker ps` 正常 |
| 沙盒镜像构建 | ✅ | `toolforge-sandbox:latest` (444MB) |
| 核心闭环 | ✅ | Plan → Search → Invent → Check → Sandbox → Register |
| Docker 安全配置 | ✅ | read_only, network=none, cap_drop=ALL 生效 |

### 🔧 修复的 Bug

详见 **[Bug Fix Log](docs/bug-fixes/2026-06-21-verification-fixes.md)**。

| # | 问题 | 层级 | 类型 |
|---|------|------|------|
| BF-01 | pyproject.toml 包发现失败 | 工程配置 | setuptools 多包检测 |
| BF-02 | auto_remove 参数重复 | 沙盒层 | 参数冲突 |
| BF-03 | container.wait API 变更 | 沙盒层 | Docker SDK 7.x 不兼容 |
| BF-04 | 测试代码静态检查过严 | Smith 层 | 改为 warning |
| BF-05 | 镜像名称不匹配 | 配置层 | 配置不一致 |

---

## 七、快速上手

```powershell
# 1. 设置 API Key
set DEEPSEEK_API_KEY=sk-你的key

# 2. 安装
cd D:\ClaudeAI\project_2
pip install -e ".[dev]"

# 3. 测试
pytest tests/ -v

# 4. 构建沙盒镜像（首次）
python -c "from toolforge.sandbox.image_builder import ImageBuilder; ImageBuilder().build(force=True)"

# 5. 运行任务
python -m toolforge.cli "你的任务描述"
```

---

## 八、已知限制（Phase 2）

1. **ReAct 循环未完全闭环** — `evaluate_failure` 已就绪但未接入主循环
2. **仅支持 DeepSeek API** — 接口已抽象，添加新适配器即可
3. **模板匹配为关键词而非语义** — 英文查询匹配不上中文模板
4. **工具调用模式未验证** — `tool_args` 参数已添加但 Agent 未使用
5. **配置不支持热重载**
6. **无结构化日志**（使用 print()）
7. **SecurityConfig 部分字段未接入**
8. **LLM 代码生成质量不足** — 自由生成路径成功率低，依赖模板匹配

---

## 九、文档索引

| 文档 | 路径 | 受众 |
|------|------|------|
| 项目状态 | `STATUS.md` | 全部 |
| **架构指南** ★ | `docs/architecture-guide.md` | 开发者 |
| **Bug Fix Log** ★ | `docs/bug-fixes/2026-06-21-verification-fixes.md` | 开发者 |
| 设计规范 | `docs/superpowers/specs/2026-05-31-toolforge-design.md` | 开发者 |
| Phase 1 计划 | `docs/superpowers/plans/2026-05-31-toolforge-phase-1.md` | 开发者 |

---

## 十、后续路线图

### Phase 2: 多 API 适配 + 核心增强
- OpenAI、Anthropic 适配器
- LLM embedding 替代 ChromaDB 默认模型
- 真正的 ReAct 循环
- 工具实际调用链路
- 结构化日志
- 安全配置完整接入
- 提高 LLM 代码生成质量

### Phase 3: Web 面板 + 协作
- Web 管理面板（FastAPI）
- 工具版本管理
- 工具分享/导出
- 多任务并发

---

## 十一、新对话快速启动

```
请阅读 STATUS.md 了解项目当前状态，然后帮我继续开发。
```
