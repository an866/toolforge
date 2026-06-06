"""Tests for Planner."""
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
