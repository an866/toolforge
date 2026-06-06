"""Tests for MasterAgent."""
import pytest
from toolforge.master.agent import MasterAgent
from toolforge.master.tool_sensor import MissingToolRequest
from toolforge.smith.smith import InventionResult
from toolforge.smith.models import GeneratedTool
from toolforge.registry.models import ToolRecord, ToolMeta, ToolSource


class MockPlanner:
    async def plan(self, task):
        return [{"description": "读取CSV文件", "required_capability": "csv_reading",
                 "expected_output": "DataFrame", "context": "用户提供了CSV文件路径"}]


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
        self._executions.append({"tool_id": tool_id, "task_id": task_id, "success": success})


class MockSensor:
    async def detect(self, capability, context):
        return MissingToolRequest(is_missing=True, tool_name="csv_reader", reason="no csv tool")
    async def evaluate_failure(self, tool_name, error_output, expected_output):
        return True


class MockSmith:
    async def invent_tool(self, name, purpose, context):
        return InventionResult(
            success=True, source="llm",
            tool=GeneratedTool(tool_name=name, description=purpose, category="test",
                               code="def read_csv(): pass", test_code="def test_read_csv(): pass"),
        )


class MockSandbox:
    async def execute(self, tool_code, test_code, metadata):
        return {"success": True, "stdout": "data", "stderr": "", "execution_time_ms": 50}


@pytest.fixture
def agent():
    return MasterAgent(
        planner=MockPlanner(), registry=MockRegistry(), sensor=MockSensor(),
        smith=MockSmith(), sandbox=MockSandbox(), max_inventions=5,
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
async def test_run_task_limits_inventions():
    class NeverEndingSensor:
        async def detect(self, *args, **kwargs):
            return MissingToolRequest(is_missing=True, tool_name="unnecessary", reason="test")
        async def evaluate_failure(self, *args, **kwargs):
            return True

    agent = MasterAgent(
        planner=MockPlanner(), registry=MockRegistry(),
        sensor=NeverEndingSensor(), smith=MockSmith(), sandbox=MockSandbox(),
        max_inventions=2,
    )
    result = await agent.run("some task")
    assert result.tools_invented <= 2
