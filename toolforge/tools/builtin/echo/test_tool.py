from tool import echo

def test_echo():
    assert echo("hello") == "hello"
    assert echo("") == ""
