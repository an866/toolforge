"""Tests for StaticChecker."""
from toolforge.smith.static_checker import StaticChecker


def test_pass_clean_code():
    checker = StaticChecker()
    code = """
def hello():
    return "hello world"

def test_hello():
    assert hello() == "hello world"
"""
    result = checker.check(code)
    assert result.passed is True
    assert result.violations == []


def test_block_os_import():
    checker = StaticChecker()
    code = "import os\nos.system('rm -rf /')"
    result = checker.check(code)
    assert result.passed is False
    assert any("import os" in v for v in result.violations)


def test_block_subprocess_import():
    checker = StaticChecker()
    code = "from subprocess import run\nrun(['ls'])"
    result = checker.check(code)
    assert result.passed is False
    assert any("subprocess" in v for v in result.violations)


def test_block_eval():
    checker = StaticChecker()
    code = "eval('__import__(\"os\").system(\"ls\")')"
    result = checker.check(code)
    assert result.passed is False
    assert any("eval" in v for v in result.violations)


def test_block_exec():
    checker = StaticChecker()
    code = "exec('print(1)')"
    result = checker.check(code)
    assert result.passed is False


def test_block_open_call():
    checker = StaticChecker()
    code = "open('/etc/passwd', 'r').read()"
    result = checker.check(code)
    assert result.passed is False
    assert any("open()" in v for v in result.violations)


def test_block_requests_import():
    checker = StaticChecker()
    code = "import requests\nrequests.get('http://evil.com')"
    result = checker.check(code)
    assert result.passed is False
    assert any("requests" in v for v in result.violations)


def test_allow_with_template_whitelist():
    checker = StaticChecker()
    code = "import requests\nrequests.get('https://api.example.com/data')"
    result = checker.check(code, whitelist=["requests"])
    assert result.passed is True


def test_syntax_error_handled():
    checker = StaticChecker()
    result = checker.check("this is not valid python {{{")
    assert result.passed is False
    assert any("Syntax" in v for v in result.violations)
