"""Master Agent — 编排核心，维护 ReAct 循环。"""
import uuid
from dataclasses import dataclass, field
from toolforge.registry.models import ToolMeta, ToolRecord, ToolSource


@dataclass
class TaskResult:
    """任务执行结果。"""
    success: bool
    steps_executed: list[str] = field(default_factory=list)
    tools_invented: int = 0
    output: str = ""
    error: str = ""


class MasterAgent:
    """主编排 Agent。协调 Planner、Registry、Sensor、Smith、Sandbox。"""

    def __init__(
        self,
        planner,
        registry,
        sensor,
        smith,
        sandbox,
        max_inventions: int = 5,
    ):
        self._planner = planner
        self._registry = registry
        self._sensor = sensor
        self._smith = smith
        self._sandbox = sandbox
        self._max_inventions = max_inventions

    async def run(self, task: str) -> TaskResult:
        """执行用户任务。"""
        result = TaskResult(success=True)
        task_id = str(uuid.uuid4())

        # 1. 分解任务
        steps = await self._planner.plan(task)
        if not steps:
            result.success = False
            result.error = "无法分解任务"
            return result

        # 2. 执行每一步
        for step in steps:
            capability = step.get("required_capability", "")
            context = step.get("context", "")
            description = step.get("description", "")

            # 搜索现有工具
            tools = await self._registry.search(capability, top_k=3)

            if not tools:
                # 感知工具缺失
                missing = await self._sensor.detect(capability, context)
                if missing.is_missing and result.tools_invented < self._max_inventions:
                    try:
                        invention = await self._smith.invent_tool(
                            name=missing.tool_name or _infer_tool_name(capability),
                            purpose=capability,
                            context=context,
                        )
                        if invention.success and invention.tool:
                            record = ToolRecord(
                                meta=ToolMeta(
                                    name=invention.tool.tool_name,
                                    description=invention.tool.description,
                                    category=invention.tool.category,
                                    source=ToolSource.AUTO,
                                    dependencies=invention.tool.dependencies,
                                    usage_example=invention.tool.usage_example,
                                ),
                                code=invention.tool.code,
                                test_code=invention.tool.test_code,
                            )
                            await self._registry.add_tool(record)
                            result.tools_invented += 1
                            tools = [record]
                    except Exception as e:
                        result.error = f"工具发明失败: {e}"
                        result.success = False
                        return result

            if not tools:
                result.error = f"步骤 '{description}' 无可用工具且无法发明新工具"
                result.success = False
                return result

            # 调用工具（通过 Docker 沙盒）
            tool = tools[0]
            sandbox_result = await self._sandbox.execute(
                tool_code=tool.code,
                test_code=tool.test_code,
                metadata={"step": description, "task_id": task_id},
            )

            tool_id = getattr(tool, "id", "")
            await self._registry.log_execution(
                tool_id=tool_id,
                task_id=task_id,
                success=sandbox_result["success"],
                execution_time_ms=sandbox_result.get("execution_time_ms", 0),
                error=sandbox_result.get("stderr", ""),
            )

            result.steps_executed.append(description)

        result.output = f"完成 {len(result.steps_executed)} 个步骤，发明了 {result.tools_invented} 个工具"
        return result


def _infer_tool_name(capability: str) -> str:
    """从能力描述推断工具名。"""
    import re
    words = capability.lower().split()[:3]
    name = "_".join(re.sub(r"[^a-z0-9_]", "", w) for w in words if w)
    return name or "generic_tool"
