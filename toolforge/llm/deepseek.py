"""DeepSeek API 适配器。"""
import json
import asyncio
import httpx
from typing import Any
from toolforge.llm.base import LLMAdapter
from toolforge.exceptions import LLMError


class DeepSeekAdapter(LLMAdapter):
    """DeepSeek V4 Pro API 适配器（兼容 OpenAI 格式）。"""

    def __init__(self, model, api_key, base_url, timeout=60, max_retries=3):
        super().__init__(model, api_key, base_url, timeout)
        self.max_retries = max_retries

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            body["tools"] = tools
        if tool_choice:
            body["tool_choice"] = tool_choice

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.max_retries):
                try:
                    resp = await client.post(
                        f"{self.base_url.rstrip('/')}/chat/completions",
                        headers=headers,
                        json=body,
                    )
                    resp.raise_for_status()
                    return resp.json()
                except httpx.HTTPStatusError as e:
                    if e.response.status_code < 500 and e.response.status_code != 429:
                        raise LLMError(
                            f"DeepSeek API error: {e.response.text}"
                        ) from e
                    if attempt == self.max_retries - 1:
                        raise LLMError(
                            f"DeepSeek API error after {self.max_retries} retries: {e.response.text}"
                        )
                    await asyncio.sleep(2 ** attempt)
                except httpx.RequestError as e:
                    if attempt == self.max_retries - 1:
                        raise LLMError(f"DeepSeek connection error: {e}")
                    await asyncio.sleep(2 ** attempt)

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        output_schema: dict[str, Any],
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        schema_str = json.dumps(output_schema, ensure_ascii=False)
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"{user_prompt}\n\n"
                    f"你必须严格按照以下 JSON schema 返回，只返回 JSON，不要包含其他文字：\n"
                    f"{schema_str}"
                ),
            },
        ]
        response = await self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=4096,
        )
        content = response["choices"][0]["message"]["content"]
        content = _strip_json_fence(content)
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise LLMError(
                f"Failed to parse structured output as JSON: {e}\n"
                f"Raw content (first 500 chars): {content[:500]}"
            )


def _strip_json_fence(text: str) -> str:
    """移除 ```json ... ``` 包裹，支持多行和行内格式。"""
    text = text.strip()
    # 行内格式: ```json{...}```
    if text.startswith("```") and text.endswith("```") and "\n" not in text:
        # 找到 JSON 内容的起始位置
        brace_idx = text.find("{")
        if brace_idx != -1:
            inner = text[brace_idx:]
        else:
            inner = text
        if inner.endswith("```"):
            inner = inner[:-3]
        return inner.strip()
    # 多行格式
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()
