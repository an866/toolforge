"""文件存储层 — 以文件系统为代码权威载体。"""
import os
import shutil
import tempfile
import yaml
from pathlib import Path
from toolforge.registry.models import ToolMeta, ToolRecord


class FileStore:
    """按 category/name 组织工具文件的存储。"""

    def __init__(self, root: str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _tool_dir(self, category: str, name: str) -> Path:
        return self.root / category / name

    def save(self, record: ToolRecord) -> Path:
        """保存工具到文件系统。返回工具目录路径。"""
        tool_dir = self._tool_dir(record.category, record.name)
        tool_dir.parent.mkdir(parents=True, exist_ok=True)

        # Write atomically: stage in temp dir, then rename
        with tempfile.TemporaryDirectory(dir=str(tool_dir.parent)) as tmpname:
            tmpdir = Path(tmpname)
            (tmpdir / "tool.py").write_text(record.code, encoding="utf-8")
            (tmpdir / "test_tool.py").write_text(record.test_code, encoding="utf-8")
            meta_dict = record.meta.model_dump(mode="json")
            (tmpdir / "meta.yaml").write_text(
                yaml.dump(meta_dict, default_flow_style=False, allow_unicode=True),
                encoding="utf-8",
            )
            # Atomically replace
            if tool_dir.exists():
                shutil.rmtree(tool_dir)
            os.rename(tmpname, str(tool_dir))
        return tool_dir

    def load(self, name: str, category: str | None = None) -> ToolRecord:
        """加载工具。如果未指定 category，遍历所有分类查找。"""
        if category:
            return self._load_from_dir(self._tool_dir(category, name))
        return self._search_and_load(name)

    def _search_and_load(self, name: str) -> ToolRecord:
        for tool_dir in self.root.rglob(name):
            if tool_dir.is_dir():
                return self._load_from_dir(tool_dir)
        raise FileNotFoundError(f"Tool not found: {name}")

    def _load_from_dir(self, tool_dir: Path) -> ToolRecord:
        if not tool_dir.exists():
            raise FileNotFoundError(f"Tool directory not found: {tool_dir}")
        try:
            code = (tool_dir / "tool.py").read_text(encoding="utf-8")
            test_code = (tool_dir / "test_tool.py").read_text(encoding="utf-8")
            meta_dict = yaml.safe_load(
                (tool_dir / "meta.yaml").read_text(encoding="utf-8")
            )
            return ToolRecord(
                meta=ToolMeta(**meta_dict),
                code=code,
                test_code=test_code,
            )
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Tool at {tool_dir} is incomplete or corrupted: {e}")
        except (yaml.YAMLError, Exception) as e:
            raise ValueError(f"Failed to load tool from {tool_dir}: {e}")

    def list_tools(self, category: str | None = None) -> list[str]:
        """列出所有工具名。"""
        names = []
        search_dir = self.root / category if category else self.root
        if not search_dir.exists():
            return []
        for meta_file in search_dir.rglob("meta.yaml"):
            tool_dir = meta_file.parent
            # Ensure this is a tool dir (has tool.py) not a subdirectory
            if (tool_dir / "tool.py").exists():
                names.append(tool_dir.name)
        return sorted(names)

    def delete(self, name: str, category: str) -> bool:
        """删除工具。返回是否实际删除了内容。"""
        tool_dir = self._tool_dir(category, name)
        if tool_dir.exists():
            shutil.rmtree(tool_dir)
            return True
        return False
