"""ToolForge 自定义异常。"""


class ToolForgeError(Exception):
    """ToolForge 基础异常。"""


class ToolNotFoundError(ToolForgeError):
    """工具库中未找到匹配工具。"""


class ToolGenerationError(ToolForgeError):
    """Tool Smith 生成工具失败。"""


class StaticCheckError(ToolForgeError):
    """静态安全检查未通过。"""
    def __init__(self, message: str, violations: list[str]):
        super().__init__(message)
        self.violations = violations


class SandboxError(ToolForgeError):
    """沙盒执行异常。"""
    def __init__(self, message: str, exit_code: int | None = None, stderr: str = ""):
        super().__init__(message)
        self.exit_code = exit_code
        self.stderr = stderr


class SandboxTimeoutError(SandboxError):
    """沙盒执行超时。"""


class ConfigError(ToolForgeError):
    """配置错误。"""


class LLMError(ToolForgeError):
    """LLM API 调用失败。"""
