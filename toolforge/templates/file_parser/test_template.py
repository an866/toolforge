from tool import parse_file


def test_parse_file():
    import tempfile, os, json
    data = {"key": "value", "number": 42}
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(data, f)
        path = f.name
    try:
        result = parse_file(filepath=path, format="json")
        assert result == data
    finally:
        os.unlink(path)
