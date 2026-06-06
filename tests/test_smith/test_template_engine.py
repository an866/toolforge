"""Tests for TemplateEngine."""
import pytest
from toolforge.smith.template_engine import TemplateEngine, ToolTemplate


@pytest.fixture
def engine(temp_dir):
    tmpl_dir = temp_dir / "templates" / "api_caller"
    tmpl_dir.mkdir(parents=True)
    (tmpl_dir / "template.yaml").write_text("""\
name: api_caller
description: "调用 HTTP API 获取数据的工具模板"
category: data_fetching
parameters:
  - name: url
    type: string
    required: true
    description: "API 端点 URL"
  - name: method
    type: choice
    options: [GET, POST]
    default: GET
whitelist:
  - requests
""", encoding="utf-8")
    (tmpl_dir / "tool_template.py").write_text("""\
import requests

def fetch_data(url="{{ url }}", method="{{ method }}"):
    if method == "GET":
        resp = requests.get(url)
    else:
        resp = requests.post(url)
    return resp.text
""", encoding="utf-8")
    (tmpl_dir / "test_template.py").write_text("""\
def test_fetch_data():
    result = fetch_data("{{ test_url }}", "{{ method }}")
    assert result is not None
""", encoding="utf-8")
    return TemplateEngine(str(tmpl_dir.parent))


def test_load_template(engine):
    tmpl = engine.get_template("api_caller")
    assert tmpl is not None
    assert tmpl.name == "api_caller"
    assert tmpl.whitelist == ["requests"]


def test_match_template(engine):
    results = engine.match("调用API获取数据")
    assert len(results) > 0
    assert results[0].name == "api_caller"


def test_no_match(engine):
    results = engine.match("x" * 100)
    assert len(results) == 0


def test_render_template(engine):
    tmpl = engine.get_template("api_caller")
    rendered = engine.render(
        tmpl,
        params={
            "url": "https://api.example.com",
            "method": "GET",
            "test_url": "https://api.example.com",
        },
    )
    assert "https://api.example.com" in rendered.code
    assert "https://api.example.com" in rendered.test_code
    assert rendered.tool_name == "api_caller"
