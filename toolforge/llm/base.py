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
