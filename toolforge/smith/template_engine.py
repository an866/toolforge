"""模板引擎 — 匹配、加载、渲染工具模板。"""
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from toolforge.smith.models import GeneratedTool


@dataclass
class ToolTemplate:
    name: str
    description: str
    category: str
    parameters: list[dict] = field(default_factory=list)
    whitelist: list[str] = field(default_factory=list)
    code_skeleton: str = ""
    test_skeleton: str = ""


class TemplateEngine:
    """管理和渲染工具模板。"""

    def __init__(self, templates_dir: str):
        self._dir = Path(templates_dir)
        self._templates: dict[str, ToolTemplate] = {}
        self._load_all()

    def _load_all(self):
        if not self._dir.exists():
            return
        for yaml_file in self._dir.rglob("template.yaml"):
            tmpl_dir = yaml_file.parent
            with open(yaml_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            code = (tmpl_dir / "tool_template.py").read_text(encoding="utf-8")
            test = (tmpl_dir / "test_template.py").read_text(encoding="utf-8")
            tmpl = ToolTemplate(
                name=data["name"],
                description=data.get("description", ""),
                category=data.get("category", ""),
                parameters=data.get("parameters", []),
                whitelist=data.get("whitelist", []),
                code_skeleton=code,
                test_skeleton=test,
            )
            self._templates[tmpl.name] = tmpl

    def get_template(self, name: str) -> ToolTemplate | None:
        return self._templates.get(name)

    def match(self, query: str) -> list[ToolTemplate]:
        """基于关键词匹配模板。返回匹配度排序的列表。"""
        import re
        query_lower = query.lower()
        scored = []
        for tmpl in self._templates.values():
            score = 0
            desc_lower = tmpl.description.lower()
            name_lower = tmpl.name.lower()
            # Split into tokens: CJK runs and ASCII words
            tokens = re.findall(r'[一-鿿]+|[a-zA-Z0-9]+', query_lower)
            for token in tokens:
                if token in desc_lower or token in name_lower:
                    score += 1
            if score > 0:
                scored.append((score, tmpl))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [tmpl for _, tmpl in scored]

    def render(self, template: ToolTemplate, params: dict[str, str]) -> GeneratedTool:
        """用参数填充模板占位符。"""
        code = template.code_skeleton
        test_code = template.test_skeleton

        for key, value in params.items():
            code = code.replace(f"{{{{ {key} }}}}", str(value))
            test_code = test_code.replace(f"{{{{ {key} }}}}", str(value))

        return GeneratedTool(
            tool_name=template.name,
            description=template.description,
            category=template.category,
            code=code,
            test_code=test_code,
        )
