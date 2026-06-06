"""Tests for ToolSmith."""
import pytest
from toolforge.smith.smith import ToolSmith, InventionResult
from toolforge.smith.static_checker import StaticChecker
from toolforge.smith.template_engine import TemplateEngine
from toolforge.smith.models import GeneratedTool


class MockCodeGenerator:
    async def generate(self, tool_name, purpose, context):
        return GeneratedTool(
            tool_name=tool_name,
            description=purpose,
            category="test",
            dependencies=[],
            code="def f(): pass",
            test_code="def test_f(): pass",
        )


class MockSandbox:
    async def execute(self, tool_code, test_code, metadata):
        return {"success": True, "stdout": "PASS", "stderr": "", "execution_time_ms": 10}


@pytest.fixture
def smith(temp_dir):
    import yaml
    tmpl_dir = temp_dir / "templates" / "test_tmpl"
    tmpl_dir.mkdir(parents=True)
    (tmpl_dir / "template.yaml").write_text(yaml.dump({
        "name": "test_tmpl",
        "description": "test template",
        "category": "test",
        "parameters": [],
        "whitelist": [],
    }))
    (tmpl_dir / "tool_template.py").write_text("def test(): pass")
    (tmpl_dir / "test_template.py").write_text("def test_test(): pass")

    engine = TemplateEngine(str(tmpl_dir.parent))
    checker = StaticChecker()
    generator = MockCodeGenerator()
    sandbox = MockSandbox()

    return ToolSmith(
        template_engine=engine,
        static_checker=checker,
        code_generator=generator,
        sandbox=sandbox,
        match_threshold=0.0,
        max_fix_attempts=2,
    )


@pytest.mark.asyncio
async def test_invent_tool_via_template(smith):
    result = await smith.invent_tool(
        name="test_tmpl",
        purpose="test template matching",
        context="testing",
    )
    assert result.success
    assert result.source == "template"
    assert result.tool is not None


@pytest.mark.asyncio
async def test_invent_tool_via_generation(smith):
    result = await smith.invent_tool(
        name="novel_tool",
        purpose="compute sha256 digest of input data with hex encoding",
        context="testing",
    )
    assert result.success
    assert result.source == "llm"


@pytest.mark.asyncio
async def test_static_check_blocks_dangerous_code(temp_dir):
    """Static check should block dangerous code before sandbox."""
    import yaml
    tmpl_dir = temp_dir / "templates" / "dangerous"
    tmpl_dir.mkdir(parents=True)
    (tmpl_dir / "template.yaml").write_text(yaml.dump({
        "name": "dangerous",
        "description": "template with dangerous code",
        "category": "test",
        "parameters": [],
        "whitelist": [],
    }))
    (tmpl_dir / "tool_template.py").write_text("import os\nos.system('rm -rf /')")
    (tmpl_dir / "test_template.py").write_text("def test(): pass")

    engine = TemplateEngine(str(tmpl_dir.parent))
    checker = StaticChecker()
    generator = MockCodeGenerator()
    sandbox = MockSandbox()

    smith = ToolSmith(
        template_engine=engine,
        static_checker=checker,
        code_generator=generator,
        sandbox=sandbox,
        match_threshold=0.0,
        max_fix_attempts=2,
    )

    from toolforge.exceptions import StaticCheckError
    with pytest.raises(StaticCheckError):
        await smith.invent_tool(name="dangerous", purpose="dangerous", context="test")
