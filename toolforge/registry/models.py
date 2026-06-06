"""Tool Registry 数据模型。"""
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class ToolSource(str, Enum):
    BUILTIN = "builtin"
    AUTO = "auto"
    VERIFIED = "verified"
    SUSPICIOUS = "suspicious"


class ToolStatus(str, Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    SUSPICIOUS = "suspicious"


class ToolMeta(BaseModel):
    """工具元数据。"""
    name: str
    version: str = "0.1.0"
    description: str
    category: str
    source: ToolSource = ToolSource.AUTO
    status: ToolStatus = ToolStatus.ACTIVE
    dependencies: list[str] = Field(default_factory=list)
    usage_example: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ToolRecord(BaseModel):
    """完整的工具记录，包含元数据、代码和测试代码。"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    meta: ToolMeta
    code: str
    test_code: str

    @property
    def name(self) -> str:
        return self.meta.name

    @property
    def category(self) -> str:
        return self.meta.category

    @property
    def source(self) -> ToolSource:
        return self.meta.source


class ExecutionRecord(BaseModel):
    """工具调用记录。"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tool_id: str
    task_id: str = ""
    success: bool
    execution_time_ms: int = 0
    sandbox_id: str = ""
    error_message: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
