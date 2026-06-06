"""ChromaDB 向量层 — 工具语义检索。"""
from typing import Optional, Callable

import chromadb
from chromadb.config import Settings


class VectorStore:
    def __init__(
        self,
        persist_path: str,
        embedding_function: Optional[Callable[[list[str]], list[list[float]]]] = None,
    ):
        self._client = chromadb.PersistentClient(
            path=persist_path,
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name="toolforge_tools",
            metadata={"hnsw:space": "cosine"},
            embedding_function=embedding_function,
        )

    def add(
        self,
        tool_id: str,
        name: str,
        description: str,
        category: str,
    ) -> None:
        self._collection.upsert(
            ids=[tool_id],
            documents=[f"{name}: {description} [category: {category}]"],
            metadatas=[{"name": name, "tool_id": tool_id}],
        )

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        count = self._collection.count()
        if count == 0:
            return []
        results = self._collection.query(
            query_texts=[query],
            n_results=min(top_k, count),
        )
        if not results["ids"] or not results["ids"][0]:
            return []

        out = []
        for i, tool_id in enumerate(results["ids"][0]):
            metadata = results["metadatas"][0][i] if results["metadatas"] else {}
            distance = results["distances"][0][i] if results["distances"] else 0
            out.append({
                "tool_id": tool_id,
                "name": metadata.get("name", ""),
                "distance": distance,
            })
        return out

    def delete(self, tool_id: str) -> None:
        self._collection.delete(ids=[tool_id])

    def count(self) -> int:
        return self._collection.count()
