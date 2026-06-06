import os
from pathlib import Path


def sys_op(operation="{{ operation }}", path="{{ path }}", env_name=""):
    if operation == "list_files":
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Path not found: {path}")
        if p.is_file():
            return {"path": str(p.absolute()), "files": [p.name], "count": 1}
        files = []
        dirs = []
        for item in p.iterdir():
            if item.is_file():
                files.append(item.name)
            elif item.is_dir():
                dirs.append(item.name)
        return {
            "path": str(p.absolute()),
            "files": files,
            "directories": dirs,
            "count": len(files) + len(dirs),
        }
    elif operation == "read_file":
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"File not found: {path}")
        content = p.read_text(encoding="utf-8")
        return {"path": str(p.absolute()), "content": content, "size": len(content)}
    elif operation == "get_env":
        value = os.environ.get(env_name, "")
        return {"name": env_name, "value": value, "exists": env_name in os.environ}
    elif operation == "get_cwd":
        cwd = Path.cwd()
        return {"cwd": str(cwd), "parts": cwd.parts}
    else:
        raise ValueError(f"Unsupported operation: {operation}")
