import os
from tool import sys_op


def test_sys_op_get_cwd():
    result = sys_op(operation="get_cwd")
    assert "cwd" in result
    assert result["cwd"] == os.getcwd()


def test_sys_op_get_env():
    result = sys_op(operation="get_env", env_name="PATH")
    assert result["exists"] is True
    assert len(result["value"]) > 0
