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


def test_strip_json_fence_inline():
    from toolforge.llm.deepseek import _strip_json_fence
    result = _strip_json_fence('```json{"key": "value"}```')
    assert result == '{"key": "value"}'


def test_strip_json_fence_inline_no_lang():
    from toolforge.llm.deepseek import _strip_json_fence
    result = _strip_json_fence('```{"key": "value"}```')
    assert result == '{"key": "value"}'


@pytest.mark.asyncio
async def test_chat_no_retry_on_401(mocker):
    import httpx
    mock_post = mocker.patch("httpx.AsyncClient.post")
    mock_response = mocker.MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"
    http_error = httpx.HTTPStatusError(
        "Unauthorized", request=mocker.MagicMock(), response=mock_response
    )
    mock_post.side_effect = http_error

    from toolforge.exceptions import LLMError
    adapter = DeepSeekAdapter(
        model="deepseek-v4-pro",
        api_key="bad-key",
        base_url="https://api.deepseek.com/v1",
    )
    with pytest.raises(LLMError, match="API error"):
        await adapter.chat([{"role": "user", "content": "hi"}])
    # Only 1 attempt (no retries)
    assert mock_post.call_count == 1


@pytest.mark.asyncio
async def test_generate_structured_parse_failure(mocker):
    mock_post = mocker.patch("httpx.AsyncClient.post")
    mock_response = mocker.MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "not valid json at all"}}]
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    from toolforge.exceptions import LLMError
    adapter = DeepSeekAdapter(
        model="deepseek-v4-pro",
        api_key="test-key",
        base_url="https://api.deepseek.com/v1",
    )
    with pytest.raises(LLMError, match="Failed to parse structured output as JSON"):
        await adapter.generate_structured(
            "system", "user",
            {"type": "object", "properties": {"key": {"type": "string"}}}
        )
