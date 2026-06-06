from tool import read_file, read_file_lines


def test_read_file():
    import tempfile, os
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("hello world")
        path = f.name
    try:
        content = read_file(path)
        assert content == "hello world"
    finally:
        os.unlink(path)


def test_read_file_lines():
    import tempfile, os
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("line1\nline2\nline3")
        path = f.name
    try:
        lines = read_file_lines(path)
        assert lines == ["line1", "line2", "line3"]
    finally:
        os.unlink(path)
