"""ToolForge CLI 入口。"""
import asyncio
import sys
from pathlib import Path
from toolforge.config import init_config, Config
from toolforge.exceptions import ToolForgeError
from toolforge.llm.base import create_adapter
from toolforge.registry.registry import ToolRegistry
from toolforge.sandbox.docker_manager import DockerManager
from toolforge.sandbox.image_builder import ImageBuilder
from toolforge.smith.smith import ToolSmith
from toolforge.smith.static_checker import StaticChecker
from toolforge.smith.template_engine import TemplateEngine
from toolforge.smith.code_generator import CodeGenerator
from toolforge.master.planner import Planner
from toolforge.master.tool_sensor import ToolSensor
from toolforge.master.agent import MasterAgent


async def main():
    config_path = Path("config.yaml")
    if config_path.exists():
        config = init_config(config_path)
    else:
        config = Config()

    dm = DockerManager(config)
    if not dm.is_available():
        print("Error: Docker is not available. Please start Docker and try again.")
        sys.exit(1)

    builder = ImageBuilder()
    if not builder.is_built():
        print("Building sandbox image (first time only)...")
        builder.build()

    adapter = create_adapter(
        provider=config.llm.provider,
        model=config.llm.model,
        api_key=config.llm.api_key,
        base_url=config.llm.base_url,
        timeout=config.llm.timeout,
    )

    registry = ToolRegistry(config)
    await registry.initialize()

    template_engine = TemplateEngine(str(Path(__file__).parent / "templates"))
    smith = ToolSmith(
        template_engine=template_engine,
        static_checker=StaticChecker(),
        code_generator=CodeGenerator(adapter),
        sandbox=dm,
        match_threshold=config.smith.template_match_threshold,
        max_fix_attempts=config.smith.max_fix_attempts,
    )

    planner = Planner(adapter)
    sensor = ToolSensor(registry=registry, adapter=adapter)

    agent = MasterAgent(
        planner=planner, registry=registry, sensor=sensor,
        smith=smith, sandbox=dm,
        max_inventions=config.security.max_inventions_per_task,
    )

    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
    else:
        print("ToolForge v0.1.0 — 自进化工具 AI Agent")
        print("Usage: toolforge <任务描述>")
        print()
        print("Example: toolforge 从PDF文件中提取所有日期")
        sys.exit(0)

    print(f"Task: {task}")
    print("-" * 50)

    try:
        result = await agent.run(task)
        if result.success:
            print(f"\nDone. {len(result.steps_executed)} steps, {result.tools_invented} tools invented.")
        else:
            print(f"\nFailed: {result.error}")
            sys.exit(1)
    except ToolForgeError as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        await registry.close()


if __name__ == "__main__":
    asyncio.run(main())
