"""Tests for DockerManager."""
import pytest
from toolforge.sandbox.docker_manager import DockerManager
from toolforge.config import Config, SandboxConfig


@pytest.fixture
def docker_manager():
    config = Config(
        sandbox=SandboxConfig(
            memory_limit_mb=128,
            timeout_seconds=10,
            pids_limit=30,
        )
    )
    return DockerManager(config)


def test_sandbox_security_config(docker_manager):
    kwargs = docker_manager._get_run_kwargs()
    assert kwargs["read_only"] is True
    assert kwargs["network_mode"] == "none"
    assert "128m" in kwargs["mem_limit"]
    assert kwargs["cap_drop"] == ["ALL"]
    assert "no-new-privileges" in kwargs["security_opt"]
    assert kwargs["auto_remove"] is True


def test_is_docker_available_runs(mocker):
    mock_client = mocker.patch("docker.from_env")
    mock_client.return_value.ping.return_value = True

    config = Config(sandbox=SandboxConfig())
    manager = DockerManager(config)
    assert manager.is_available() is True


def test_is_docker_unavailable(mocker):
    mock_client = mocker.patch("docker.from_env")
    mock_client.side_effect = Exception("Docker not running")

    config = Config(sandbox=SandboxConfig())
    manager = DockerManager(config)
    assert manager.is_available() is False
