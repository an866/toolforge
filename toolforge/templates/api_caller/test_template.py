from tool import api_call

def test_api_call_get():
    result = api_call(url="{{ url }}", method="{{ method }}")
    assert "status_code" in result
