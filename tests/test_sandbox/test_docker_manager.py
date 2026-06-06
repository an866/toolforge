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


def test_build_sandbox_args(docker_manager):
    args = docker_manager._build_container_args()
    assert "--read-only" in args
    assert "--network=none" in args
    assert "--memory=128m" in args
    assert "--cpus=1" in args
    assert "--pids-limit=30" in args
    assert "--cap-drop=ALL" in args
    assert "--security-opt=no-new-privileges" in args


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
