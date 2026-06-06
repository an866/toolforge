"""构建沙盒 Docker 镜像。"""
from pathlib import Path
from toolforge.exceptions import SandboxError


class ImageBuilder:
    """构建预装依赖的沙盒镜像。"""

    SANDBOX_IMAGE = "toolforge-sandbox:latest"
    _dockerfile_path = Path(__file__).parent.parent.parent / "sandbox" / "Dockerfile"

    def __init__(self):
        self._docker = None

    def _get_docker(self):
        if self._docker is None:
            import docker
            self._docker = docker.from_env()
        return self._docker

    def build(self, force: bool = False) -> str:
        """构建沙盒镜像。返回镜像 tag。"""
        docker = self._get_docker()
        if not force:
            try:
                docker.images.get(self.SANDBOX_IMAGE)
                return self.SANDBOX_IMAGE
            except Exception:
                pass

        dockerfile_dir = str(self._dockerfile_path.parent)
        if not self._dockerfile_path.exists():
            raise SandboxError(f"Dockerfile not found at {self._dockerfile_path}")

        image, _ = docker.images.build(
            path=dockerfile_dir,
            tag=self.SANDBOX_IMAGE,
            rm=True,
        )
        return image.id

    def is_built(self) -> bool:
        try:
            self._get_docker().images.get(self.SANDBOX_IMAGE)
            return True
        except Exception:
            return False
