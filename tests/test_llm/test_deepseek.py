"""Tests for DeepSeekAdapter."""
import pytest
from toolforge.llm.deepseek import DeepSeekAdapter


def test_deepseek_adapter_initialization():
    adapter = DeepSeekAdapter(
        model="deepseek-v4-pro",
        api_key="test-key",
        base_url="https://api.deepseek.com/v1",
    )
    assert adapter.model == "deepseek-v4-pro"
    assert adapter.api_key == "test-key"
    assert adapter.base_url == "https://api.deepseek.com/v1"


@pytest.mark.asyncio
async def test_chat_makes_correct_api_call(mocker):
    mock_post = mocker.patch("httpx.AsyncClient.post")
    mock_response = mocker.MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "你好"}}]
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    adapter = DeepSeekAdapter(
        model="deepseek-v4-pro",
        api_key="test-key",
        base_url="https://api.deepseek.com/v1",
    )
    result = await adapter.chat([{"role": "user", "content": "你好"}])
    assert result["choices"][0]["message"]["content"] == "你好"


@pytest.mark.asyncio
async def test_generate_structured_parses_json(mocker):
    mock_post = mocker.patch("httpx.AsyncClient.post")
    mock_response = mocker.MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": '{"key": "value"}'}}]
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    adapter = DeepSeekAdapter(
        model="deepseek-v4-pro",
        api_key="test-key",
        base_url="https://api.deepseek.com/v1",
    )
    result = await adapter.generate_structured(
        "system", "user",
        {"type": "object", "properties": {"key": {"type": "string"}}}
    )
    assert result == {"key": "value"}


def test_create_adapter_factory():
    from toolforge.llm.base import create_adapter
    adapter = create_adapter(
        "deepseek",
        model="deepseek-v4-pro",
        api_key="test-key",
        base_url="https://api.deepseek.com/v1",
    )
    assert isinstance(adapter, DeepSeekAdapter)


def test_create_adapter_unknown_provider():
    from toolforge.llm.base import create_adapter
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        create_adapter("unknown")


def test_strip_json_fence():
    from toolforge.llm.deepseek import _strip_json_fence
    result = _strip_json_fence('```json\n{"key": "value"}\n```')
    assert result == '{"key": "value"}'

    result2 = _strip_json_fence('{"key": "value"}')
    assert result2 == '{"key": "value"}'
