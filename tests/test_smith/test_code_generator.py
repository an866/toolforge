"""Tests for CodeGenerator."""
import pytest
from toolforge.smith.code_generator import CodeGenerator, _SYSTEM_PROMPT
from toolforge.llm.base import LLMAdapter


class MockAdapter(LLMAdapter):
    def __init__(self):
        super().__init__(model="mock", api_key="", base_url="")

    async def chat(self, messages, tools=None, tool_choice=None, temperature=0.7, max_tokens=4096):
        return {"choices": [{"message": {"content": "{}"}}]}

    async def generate_structured(self, system_prompt, user_prompt, output_schema, temperature=0.3):
        return {
            "tool_name": "pdf_extractor",
            "version": "0.1.0",
            "description": "Extract text from PDF files",
            "category": "document_processing",
            "dependencies": ["PyPDF2"],
            "code": "import PyPDF2\n\ndef extract_pdf(path):\n    reader = PyPDF2.PdfReader(path)\n    return '\\n'.join([p.extract_text() for p in reader.pages])",
            "test_code": "def test_extract_pdf():\n    pass",
            "usage_example": "extract_pdf('file.pdf')",
        }


@pytest.mark.asyncio
async def test_generate_tool():
    gen = CodeGenerator(adapter=MockAdapter())
    result = await gen.generate(
        tool_name="pdf_extractor",
        purpose="从PDF文件中提取文本内容",
        context="用户上传了一个PDF文件，需要读取其中的内容",
    )
    assert result.tool_name == "pdf_extractor"
    assert result.category == "document_processing"
    assert "PyPDF2" in result.code


@pytest.mark.asyncio
async def test_generate_sets_source():
    gen = CodeGenerator(adapter=MockAdapter())
    result = await gen.generate(tool_name="test_tool", purpose="test", context="test")
    assert result.source == "llm_generated"


def test_system_prompt_contains_security():
    assert "eval" in _SYSTEM_PROMPT
    assert "Docker" in _SYSTEM_PROMPT
