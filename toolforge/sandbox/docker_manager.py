"""Docker 沙盒管理 — 容器创建、执行、销毁。"""
import json
import asyncio
import tempfile
from pathlib import Path
from toolforge.config import Config
from toolforge.exceptions import SandboxError, SandboxTimeoutError


class DockerManager:
    def __init__(self, config: Config):
        self._config = config
        self._docker = None

    def _get_docker(self):
        if self._docker is None:
            import docker
            self._docker = docker.from_env()
        return self._docker

    def is_available(self) -> bool:
        try:
            self._get_docker().ping()
            return True
        except Exception:
            return False

    async def execute(
        self,
        tool_code: str,
        test_code: str,
        metadata: dict,
    ) -> dict:
        """在沙盒中执行工具代码和测试代码。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            (tmp / "tool.py").write_text(tool_code, encoding="utf-8")
            (tmp / "test_tool.py").write_text(test_code, encoding="utf-8")
            (tmp / "run_tests.py").write_text(_RUNNER_SCRIPT, encoding="utf-8")

            timeout = self._config.sandbox.timeout_seconds
            docker = self._get_docker()
            container = None

            try:
                container = docker.containers.run(
                    image=self._config.sandbox.base_image,
                    command=["python", "/code/run_tests.py"],
                    volumes={str(tmp): {"bind": "/code", "mode": "ro"}},
                    working_dir="/code",
                    detach=True,
                    auto_remove=True,
                    **self._get_run_kwargs(),
                )

                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(None, container.wait, timeout)

                logs = container.logs(stdout=True, stderr=True).decode("utf-8", errors="replace")

                try:
                    test_result = json.loads(logs.split("\n__RESULT__\n")[-1].strip())
                except (json.JSONDecodeError, IndexError):
                    test_result = {
                        "passed": False,
                        "output": logs,
                        "error": "Failed to parse test results",
                    }

                return {
                    "success": test_result.get("passed", False),
                    "exit_code": result.get("StatusCode", -1),
                    "stdout": test_result.get("output", ""),
                    "stderr": test_result.get("error", ""),
                    "execution_time_ms": test_result.get("execution_time_ms", 0),
                }

            except Exception as e:
                timeout_keywords = ("timeout", "timed out")
                if any(kw in str(e).lower() for kw in timeout_keywords):
                    raise SandboxTimeoutError(f"Sandbox execution timed out: {e}")
                raise SandboxError(f"Sandbox execution failed: {e}", stderr=str(e))
            finally:
                if container is not None:
                    try:
                        container.remove(force=True)
                    except Exception:
                        pass  # Best effort cleanup

    def _get_run_kwargs(self) -> dict:
        return {
            "read_only": True,
            "network_mode": "none",
            "mem_limit": f"{self._config.sandbox.memory_limit_mb}m",
            "memswap_limit": f"{self._config.sandbox.memory_limit_mb}m",
            "nano_cpus": int(self._config.sandbox.cpu_limit * 1_000_000_000),
            "pids_limit": self._config.sandbox.pids_limit,
            "tmpfs": {"/tmp": "size=64m,noexec"},
            "cap_drop": ["ALL"],
            "security_opt": ["no-new-privileges"],
            "ulimits": [{"name": "nofile", "soft": 64, "hard": 64}],
            "auto_remove": True,
        }

    async def verify_sandbox(self) -> bool:
        """快速验证沙盒是否可正常工作。"""
        try:
            result = await self.execute(
                tool_code="def hello():\n    return 'ok'",
                test_code="""import json
import sys
import time
from tool import hello
def test_hello():
    assert hello() == 'ok'
if __name__ == '__main__':
    start = time.time()
    try:
        test_hello()
        print("__RESULT__")
        print(json.dumps({"passed": True, "execution_time_ms": int((time.time()-start)*1000)}))
    except Exception as e:
        print("__RESULT__")
        print(json.dumps({"passed": False, "error": str(e), "execution_time_ms": 0}))""",
                metadata={"name": "sandbox_test"},
            )
            return result["success"]
        except SandboxError:
            return False


_RUNNER_SCRIPT = '''import json
import sys
import time
import traceback

from tool import *
from test_tool import *

def run_all_tests():
    passed = 0
    failed = 0
    output_lines = []
    error_lines = []

    test_funcs = [
        (name, obj) for name, obj in globals().items()
        if name.startswith("test_") and callable(obj)
    ]

    for name, func in test_funcs:
        try:
            func()
            passed += 1
            output_lines.append(f"PASS: {name}")
        except AssertionError as e:
            failed += 1
            error_lines.append(f"FAIL: {name} - {e}")
        except Exception as e:
            failed += 1
            error_lines.append(f"ERROR: {name} - {e}\\n{traceback.format_exc()}")

    return {
        "passed": failed == 0,
        "output": "\\n".join(output_lines + error_lines),
        "error": "\\n".join(error_lines) if error_lines else "",
        "passed_count": passed,
        "failed_count": failed,
    }


if __name__ == "__main__":
    start = time.time()
    try:
        result = run_all_tests()
        result["execution_time_ms"] = int((time.time() - start) * 1000)
    except Exception as e:
        result = {
            "passed": False,
            "output": "",
            "error": f"Test runner crashed: {e}\\n{traceback.format_exc()}",
            "execution_time_ms": 0,
        }

    print("__RESULT__")
    print(json.dumps(result))
'''
