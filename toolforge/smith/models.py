"""Tool Smith 数据模型 — 生成产物结构。"""
from pydantic import BaseModel, Field


class GeneratedTool(BaseModel):
    """LLM 生成的工具产物。"""
    tool_name: str
    version: str = "0.1.0"
    description: str
    category: str
    dependencies: list[str] = Field(default_factory=list)
    code: str
    test_code: str
    usage_example: str = ""
    source: str = "llm_generated"


class StaticCheckResult(BaseModel):
    """静态检查结果。"""
    passed: bool
    violations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
