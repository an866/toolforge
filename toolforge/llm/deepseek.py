"""DeepSeek API 适配器。"""
import json
import asyncio
import httpx
from typing import Any
from toolforge.llm.base import LLMAdapter
from toolforge.exceptions import LLMError


class DeepSeekAdapter(LLMAdapter):
    """DeepSeek V4 Pro API 适配器（兼容 OpenAI 格式）。"""

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
            for attempt in range(3):
                try:
                    resp = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=body,
                    )
                    resp.raise_for_status()
                    return resp.json()
                except httpx.HTTPStatusError as e:
                    if attempt == 2:
                        raise LLMError(
                            f"DeepSeek API error after 3 retries: {e.response.text}"
                        )
                    await asyncio.sleep(2 ** attempt)
                except httpx.RequestError as e:
                    if attempt == 2:
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
            raise LLMError(f"Failed to parse structured output as JSON: {e}")


def _strip_json_fence(text: str) -> str:
    """移除 ```json ... ``` 包裹。"""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()
