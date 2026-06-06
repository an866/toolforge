"""Tests for FileStore."""
import pytest
from toolforge.registry.file_store import FileStore
from toolforge.registry.models import ToolMeta, ToolRecord, ToolSource


def test_save_and_load_tool(temp_dir):
    store = FileStore(str(temp_dir))
    record = ToolRecord(
        meta=ToolMeta(
            name="hello_world",
            description="A hello world tool",
            category="test",
            source=ToolSource.AUTO,
        ),
        code="def hello():\n    return 'hello'",
        test_code="def test_hello():\n    assert hello() == 'hello'",
    )
    store.save(record)

    loaded = store.load("hello_world")
    assert loaded.name == "hello_world"
    assert loaded.code == "def hello():\n    return 'hello'"
    assert loaded.test_code == "def test_hello():\n    assert hello() == 'hello'"


def test_load_nonexistent_tool(temp_dir):
    store = FileStore(str(temp_dir))
    with pytest.raises(FileNotFoundError):
        store.load("nonexistent")


def test_list_tools_by_category(temp_dir):
    store = FileStore(str(temp_dir))
    for i in range(3):
        record = ToolRecord(
            meta=ToolMeta(
                name=f"tool_{i}",
                description=f"Tool {i}",
                category="test_cat",
                source=ToolSource.AUTO,
            ),
            code=f"def tool_{i}(): pass",
            test_code=f"def test_tool_{i}(): pass",
        )
        store.save(record)

    names = store.list_tools(category="test_cat")
    assert len(names) == 3
    assert "tool_0" in names


def test_list_tools_without_category(temp_dir):
    store = FileStore(str(temp_dir))
    for i in range(2):
        record = ToolRecord(
            meta=ToolMeta(
                name=f"global_{i}",
                description=f"Tool {i}",
                category=f"cat_{i}",
                source=ToolSource.AUTO,
            ),
            code=f"def global_{i}(): pass",
            test_code=f"def test_global_{i}(): pass",
        )
        store.save(record)

    names = store.list_tools()
    assert len(names) == 2
    assert "global_0" in names
    assert "global_1" in names


def test_delete_tool(temp_dir):
    store = FileStore(str(temp_dir))
    record = ToolRecord(
        meta=ToolMeta(name="temp_tool", description="temp", category="test"),
        code="pass",
        test_code="pass",
    )
    store.save(record)
    assert store.delete("temp_tool", "test") is True
    assert store.delete("temp_tool", "test") is False  # already gone
    with pytest.raises(FileNotFoundError):
        store.load("temp_tool", "test")
