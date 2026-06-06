"""共享测试 fixtures。"""
import pytest
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def temp_dir():
    """创建临时目录，测试后自动清理。"""
    d = tempfile.mkdtemp()
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def sample_config():
    """返回用于测试的配置字典。"""
    return {
        "llm": {
            "provider": "deepseek",
            "api_key": "test-key",
            "model": "deepseek-v4-pro",
            "base_url": "https://api.deepseek.com/v1",
        },
        "sandbox": {
            "memory_limit_mb": 128,
            "timeout_seconds": 10,
        },
        "smith": {
            "template_match_threshold": 0.7,
            "max_fix_attempts": 2,
        },
        "registry": {
            "db_path": ":memory:",
            "tools_path": "/tmp/test_tools",
        },
        "security": {
            "human_approval_mode": False,
            "max_inventions_per_task": 3,
            "rate_limit_per_tool": 50,
        },
    }
