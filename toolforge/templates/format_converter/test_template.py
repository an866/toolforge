import json
from tool import convert


def test_convert_json_to_csv():
    data = [
        {"name": "Alice", "age": 30},
        {"name": "Bob", "age": 25},
    ]
    input_str = json.dumps(data)
    result = convert(data=input_str, input_format="json", output_format="csv")
    lines = result.strip().split("\n")
    assert len(lines) == 3  # header + 2 rows
    assert "Alice" in result
