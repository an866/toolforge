"""Tests for DBStore."""
import pytest
import pytest_asyncio
from toolforge.registry.db_store import DBStore
from toolforge.registry.models import ToolMeta, ToolRecord, ToolSource, ExecutionRecord


@pytest_asyncio.fixture
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
    assert result["name"] == "test_tool"


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


@pytest.mark.asyncio
async def test_get_tool_by_name(db):
    record = ToolRecord(
        meta=ToolMeta(name="named_tool", description="named", category="test"),
        code="code",
        test_code="test",
    )
    await db.insert_tool(record)
    result = await db.get_tool_by_name("named_tool")
    assert result is not None
    assert result["name"] == "named_tool"


@pytest.mark.asyncio
async def test_get_nonexistent_tool(db):
    result = await db.get_tool("nonexistent-id")
    assert result is None


@pytest.mark.asyncio
async def test_get_stats_for_zero_executions(db):
    record = ToolRecord(
        meta=ToolMeta(name="untouched", description="desc", category="test"),
        code="code",
        test_code="test",
    )
    await db.insert_tool(record)
    stats = await db.get_tool_stats(record.id)
    assert stats["total_calls"] == 0
    assert stats["success_rate"] == 0.0


@pytest.mark.asyncio
async def test_update_tool_status(db):
    record = ToolRecord(
        meta=ToolMeta(name="status_test", description="desc", category="test"),
        code="code",
        test_code="test",
    )
    await db.insert_tool(record)
    from toolforge.registry.models import ToolStatus
    await db.update_tool_status(record.id, ToolStatus.DEPRECATED)
    result = await db.get_tool(record.id)
    assert result["status"] == "deprecated"
