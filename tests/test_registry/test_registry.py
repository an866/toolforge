"""Tests for ToolRegistry unified interface."""
import pytest
import pytest_asyncio
from toolforge.registry.registry import ToolRegistry
from toolforge.registry.models import ToolMeta, ToolRecord, ToolSource
from toolforge.config import Config, RegistryConfig


@pytest_asyncio.fixture
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
    assert results[0].id == record.id  # ID matches


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
