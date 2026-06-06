"""LLM 代码生成器 — 让 LLM 从零生成工具代码。"""
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
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            output_schema=schema,
        )
        return GeneratedTool(**result)


_SYSTEM_PROMPT = """你是一个专业的 Python 工具开发者。你的任务是生成高质量、安全、可测试的 Python 工具代码。

要求：
1. 代码必须完整、可直接运行
2. 必须包含测试函数（函数名以 test_ 开头）
3. 测试要覆盖正常场景和边界情况
4. 禁止使用危险模块：os, subprocess, sys, eval, exec, ctypes
5. 禁止直接读写文件系统（除非工具功能明确需要）
6. 添加适当的类型注解和 docstring
7. 依赖列表要准确完整

你的输出将经过静态安全检查和 Docker 沙盒验证，只有通过验证的工具才会被采纳。"""
