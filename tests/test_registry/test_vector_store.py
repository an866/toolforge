"""Tests for VectorStore."""
import hashlib

import pytest

from toolforge.registry.vector_store import VectorStore


class FakeEmbeddingFunction:
    """Minimal deterministic embedding for tests — no model download needed."""

    def __call__(self, input: list[str]) -> list[list[float]]:
        dim = 64

        def _hash_vector(text: str) -> list[float]:
            vec = [0.0] * dim
            for ch in text:
                h = int(hashlib.sha256(ch.encode()).hexdigest(), 16)
                idx = h % dim
                vec[idx] += 1.0
            norm = sum(v * v for v in vec) ** 0.5
            if norm > 0:
                vec = [v / norm for v in vec]
            return vec

        return [_hash_vector(t) for t in input]

    def embed_query(self, input: list[str]) -> list[list[float]]:
        return self(input)

    @staticmethod
    def name() -> str:
        return "fake_embedding"

    @staticmethod
    def is_legacy() -> bool:
        return False

    @staticmethod
    def default_space() -> str:
        return "cosine"

    @staticmethod
    def supported_spaces() -> list[str]:
        return ["cosine", "l2", "ip"]


@pytest.fixture
def vector_store(temp_dir):
    return VectorStore(
        str(temp_dir / "chromadb"),
        embedding_function=FakeEmbeddingFunction(),
    )


def test_add_and_search(vector_store):
    vector_store.add(
        tool_id="tool_1",
        name="http_get",
        description="发送HTTP GET请求获取网页内容",
        category="data_fetching",
    )
    vector_store.add(
        tool_id="tool_2",
        name="pdf_parser",
        description="解析PDF文件并提取文本内容",
        category="document_processing",
    )

    results = vector_store.search("下载网页", top_k=2)
    assert len(results) > 0
    assert results[0]["name"] == "http_get"


def test_delete_tool(vector_store):
    vector_store.add(
        tool_id="temp_tool",
        name="temp",
        description="Temporary tool",
        category="test",
    )
    vector_store.delete("temp_tool")
    results = vector_store.search("temp", top_k=5)
    assert not any(r["name"] == "temp" for r in results)


def test_search_returns_empty_for_no_match(vector_store):
    results = vector_store.search("完全不相关的查询xyz123", top_k=5)
    assert results == []


def test_count(vector_store):
    assert vector_store.count() == 0
    vector_store.add(tool_id="t1", name="test", description="test", category="test")
    assert vector_store.count() == 1
