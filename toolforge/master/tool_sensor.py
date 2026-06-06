"""工具缺失感知器 — 双重触发机制。"""
from dataclasses import dataclass
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
        """触发路径 1: LLM 主动感知 — 注册表中无匹配工具。"""
        existing = await self._registry.search(capability, top_k=3)
        if existing:
            return MissingToolRequest(is_missing=False)

        result = await self._adapter.generate_structured(
            system_prompt=_SENSOR_SYSTEM_PROMPT,
            user_prompt=f"任务需要的能力: {capability}\n上下文: {context}",
            output_schema={
                "type": "object",
                "properties": {
                    "missing": {"type": "boolean"},
                    "tool_name": {"type": "string"},
                    "reason": {"type": "string"},
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
        """触发路径 2: 失败驱动 — 工具执行后结果不符合预期。"""
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

_FAILURE_SYSTEM_PROMPT = """你是一个工具质量评估专家。分析工具执行结果，判断失败是因为工具能力不足（需要更强或不同的工具），还是因为输入数据有问题。

如果工具本身的功能无法满足需求（如只能处理文本但需要处理表格），标记为工具能力不足。"""
