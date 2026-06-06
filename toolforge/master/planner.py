"""任务分解器 — 将用户任务拆解为可执行的步骤序列。"""
from toolforge.llm.base import LLMAdapter


class Planner:
    """使用 LLM 将复杂任务分解为有序步骤。"""

    def __init__(self, adapter: LLMAdapter):
        self._adapter = adapter

    async def plan(self, task: str) -> list[dict]:
        schema = {
            "type": "object",
            "properties": {
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": {"type": "string"},
                            "required_capability": {"type": "string"},
                            "expected_output": {"type": "string"},
                            "context": {"type": "string"},
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
4. 命名规范：工具名使用 snake_case
5. 步骤数量控制在 2-6 个"""
