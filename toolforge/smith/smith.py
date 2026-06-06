"""Tool Smith 统一接口 — 协调模板匹配、代码生成、静态检查和沙盒验证。"""
from dataclasses import dataclass
from toolforge.smith.models import GeneratedTool
from toolforge.smith.template_engine import TemplateEngine
from toolforge.smith.static_checker import StaticChecker
from toolforge.smith.code_generator import CodeGenerator
from toolforge.exceptions import ToolGenerationError, StaticCheckError


@dataclass
class InventionResult:
    """工具发明结果。"""
    success: bool
    tool: GeneratedTool | None = None
    source: str = ""
    error: str = ""


class ToolSmith:
    """工具发明工厂。"""

    def __init__(
        self,
        template_engine: TemplateEngine,
        static_checker: StaticChecker,
        code_generator: CodeGenerator,
        sandbox,
        match_threshold: float = 0.7,
        max_fix_attempts: int = 2,
    ):
        self._templates = template_engine
        self._checker = static_checker
        self._generator = code_generator
        self._sandbox = sandbox
        self._match_threshold = match_threshold
        self._max_fix_attempts = max_fix_attempts

    async def invent_tool(
        self,
        name: str,
        purpose: str,
        context: str,
    ) -> InventionResult:
        """发明新工具：模板匹配 > LLM 生成 > 静态检查 > 沙盒验证。"""
        generated: GeneratedTool | None = None
        source = ""

        # 1. 尝试模板匹配
        matches = self._templates.match(purpose)
        if matches:
            tmpl = matches[0]
            params = self._extract_params(tmpl, purpose)
            generated = self._templates.render(tmpl, params)
            generated.tool_name = name
            source = "template"

        # 2. LLM 自由生成
        if generated is None:
            generated = await self._generator.generate(
                tool_name=name,
                purpose=purpose,
                context=context,
            )
            source = "llm"

        # 3. 静态检查
        whitelist = matches[0].whitelist if matches else []
        check_result = self._checker.check(generated.code, whitelist=whitelist)
        check_result_test = self._checker.check(generated.test_code, whitelist=whitelist)

        if not check_result.passed:
            raise StaticCheckError(
                f"Static check failed: {'; '.join(check_result.violations)}",
                violations=check_result.violations,
            )
        if not check_result_test.passed:
            raise StaticCheckError(
                f"Test code static check failed: {'; '.join(check_result_test.violations)}",
                violations=check_result_test.violations,
            )

        # 4. 沙盒验证
        for attempt in range(self._max_fix_attempts + 1):
            sandbox_result = await self._sandbox.execute(
                tool_code=generated.code,
                test_code=generated.test_code,
                metadata={
                    "name": name,
                    "purpose": purpose,
                    "dependencies": generated.dependencies,
                },
            )

            if sandbox_result["success"]:
                return InventionResult(
                    success=True,
                    tool=generated,
                    source=source,
                )

            # 修正尝试
            if attempt < self._max_fix_attempts and source == "llm":
                generated = await self._fix_tool(
                    generated,
                    sandbox_result.get("stderr", sandbox_result.get("stdout", "")),
                )

        raise ToolGenerationError(
            f"Tool generation failed after {self._max_fix_attempts} fix attempts"
        )

    def _extract_params(self, template, purpose: str) -> dict[str, str]:
        """从目的描述中提取模板参数。"""
        params = {}
        for p in template.parameters:
            params[p["name"]] = p.get("default", "")
        return params

    async def _fix_tool(self, tool: GeneratedTool, error_output: str) -> GeneratedTool:
        """根据沙盒错误信息让 LLM 修正代码。"""
        return await self._generator.generate(
            tool_name=tool.tool_name,
            purpose=f"修复以下工具的错误。原始描述: {tool.description}",
            context=f"代码运行错误:\n{error_output}\n\n原始代码:\n{tool.code}",
        )
