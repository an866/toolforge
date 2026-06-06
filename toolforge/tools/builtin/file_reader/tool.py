"""读取文件内容的工具。"""
from pathlib import Path


def read_file(filepath: str, encoding: str = "utf-8") -> str:
    p = Path(filepath)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    return p.read_text(encoding=encoding)


def read_file_lines(filepath: str, encoding: str = "utf-8") -> list[str]:
    content = read_file(filepath, encoding)
    return content.splitlines()
