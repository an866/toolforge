"""Tests for ToolSensor."""
import pytest
from toolforge.master.tool_sensor import ToolSensor, MissingToolRequest


class MockRegistry:
    def __init__(self, results=None):
        self.results = results or []
    async def search(self, query, top_k=5):
        return self.results


class MockAdapter:
    async def generate_structured(self, system_prompt, user_prompt, output_schema, temperature=0.3):
        required = output_schema.get("required", [])
        if "is_tool_inadequate" in required:
            return {"is_tool_inadequate": True, "explanation": "工具无法处理表格数据"}
        return {"missing": True, "tool_name": "pdf_table_extractor", "reason": "无法处理表格"}


@pytest.mark.asyncio
async def test_detect_missing_tool_no_match():
    registry = MockRegistry(results=[])
    sensor = ToolSensor(registry=registry, adapter=MockAdapter())
    result = await sensor.detect(capability="从PDF中提取表格", context="PDF包含财务报表")
    assert result.is_missing is True
    assert result.tool_name == "pdf_table_extractor"


@pytest.mark.asyncio
async def test_detect_existing_tool_no_missing():
    registry = MockRegistry(results=[{"name": "existing_tool"}])
    sensor = ToolSensor(registry=registry, adapter=MockAdapter())
    result = await sensor.detect(capability="已有工具", context="test")
    assert result.is_missing is False


@pytest.mark.asyncio
async def test_evaluate_failure():
    registry = MockRegistry(results=[])
    sensor = ToolSensor(registry=registry, adapter=MockAdapter())
    is_inadequate = await sensor.evaluate_failure(
        tool_name="pdf_extract_text",
        error_output="乱码文本，表格数据丢失",
        expected_output="结构化的表格数据",
    )
    assert is_inadequate is True
