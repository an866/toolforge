"""AST 静态安全检查器 — 分析代码中的危险调用而不执行。"""
import ast
from toolforge.smith.models import StaticCheckResult


class StaticChecker:
    """基于 AST 的代码安全检查器。"""

    FORBIDDEN_IMPORTS = {
        "os", "subprocess", "sys", "ctypes", "pickle", "shutil",
        "socket", "requests", "urllib", "http.client",
    }

    FORBIDDEN_CALLS = {
        "eval", "exec", "compile", "__import__", "open", "input",
    }

    def check(self, code: str, whitelist: list[str] | None = None) -> StaticCheckResult:
        whitelist_set = set(whitelist or [])
        violations: list[str] = []

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return StaticCheckResult(
                passed=False,
                violations=[f"Syntax error: {e}"],
            )

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    base_module = alias.name.split(".")[0]
                    if base_module in self.FORBIDDEN_IMPORTS and base_module not in whitelist_set:
                        violations.append(f"Blocked import: import {alias.name}")

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    base_module = node.module.split(".")[0]
                    if base_module in self.FORBIDDEN_IMPORTS and base_module not in whitelist_set:
                        violations.append(f"Blocked import: from {node.module} import ...")

            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in self.FORBIDDEN_CALLS:
                        violations.append(f"Blocked call: {node.func.id}()")
                elif isinstance(node.func, ast.Attribute):
                    if node.func.attr in self.FORBIDDEN_CALLS:
                        violations.append(f"Blocked call: .{node.func.attr}()")

        return StaticCheckResult(
            passed=len(violations) == 0,
            violations=violations,
        )
