from tool import process_text


def test_process_text_search():
    result = process_text(text="hello world 123", pattern="\\d+", operation="search")
    assert result["found"] is True
    assert result["match"] == "123"


def test_process_text_extract():
    result = process_text(text="apple, banana, cherry", pattern="\\w+", operation="extract")
    assert result["matches"] == ["apple", "banana", "cherry"]
    assert result["count"] == 3
