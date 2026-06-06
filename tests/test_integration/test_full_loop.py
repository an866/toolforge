"""End-to-end integration tests for the full tool invention loop."""
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
        "success": True, "stdout": "result data", "stderr": "", "execution_time_ms": 50,
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
        is_missing=True, tool_name="test_generated_tool", reason="no existing tool",
    )
    mock.evaluate_failure.return_value = False
    return mock


def _make_mock_smith():
    mock = AsyncMock()
    mock.invent_tool.return_value = InventionResult(
        success=True, source="llm",
        tool=GeneratedTool(
            tool_name="test_generated_tool", description="auto-generated tool",
            category="test", code="def run(): return 'ok'",
            test_code="def test_run(): assert run() == 'ok'",
        ),
    )
    return mock


def _make_mock_planner():
    mock = AsyncMock()
    mock.plan.return_value = [
        {"description": "Step 1: process data", "required_capability": "data_processing",
         "expected_output": "processed data", "context": "user has raw data"},
    ]
    return mock


@pytest.mark.asyncio
async def test_full_loop_single_step():
    """Full loop: plan -> detect missing -> invent -> verify -> execute -> log"""
    agent = MasterAgent(
        planner=_make_mock_planner(), registry=_make_mock_registry(),
        sensor=_make_mock_sensor(), smith=_make_mock_smith(),
        sandbox=_make_mock_sandbox(), max_inventions=5,
    )
    result = await agent.run("process some raw data")
    assert result.success is True
    assert result.tools_invented == 1
    assert len(result.steps_executed) == 1


@pytest.mark.asyncio
async def test_full_loop_uses_existing_tool():
    """When tool exists, don't invent, use directly."""
    registry = _make_mock_registry()
    registry.search.return_value = [
        ToolRecord(
            meta=ToolMeta(name="existing_tool", description="already exists",
                          category="test", source=ToolSource.BUILTIN),
            code="def run(): return 'ok'", test_code="def test_run(): pass",
        )
    ]
    sensor = _make_mock_sensor()
    sensor.detect.return_value = MissingToolRequest(is_missing=False)

    agent = MasterAgent(
        planner=_make_mock_planner(), registry=registry,
        sensor=sensor, smith=_make_mock_smith(),
        sandbox=_make_mock_sandbox(), max_inventions=5,
    )
    result = await agent.run("use existing tool")
    assert result.tools_invented == 0
    assert len(result.steps_executed) == 1


@pytest.mark.asyncio
async def test_full_loop_tool_generation_failure():
    """When tool generation fails, task should fail."""
    smith = _make_mock_smith()
    smith.invent_tool.side_effect = Exception("generation crashed")

    agent = MasterAgent(
        planner=_make_mock_planner(), registry=_make_mock_registry(),
        sensor=_make_mock_sensor(), smith=smith,
        sandbox=_make_mock_sandbox(), max_inventions=5,
    )
    result = await agent.run("impossible task")
    assert result.success is False
    assert "generation crashed" in result.error
