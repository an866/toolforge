"""Tool Registry 统一接口 — 协调三层存储。"""
from toolforge.config import Config
from toolforge.registry.models import ToolMeta, ToolRecord, ToolSource, ToolStatus, ExecutionRecord
from toolforge.registry.file_store import FileStore
from toolforge.registry.db_store import DBStore
from toolforge.registry.vector_store import VectorStore


class ToolRegistry:
    """三层存储的统一入口。"""

    def __init__(self, config: Config):
        self._config = config
        self._file_store = FileStore(config.registry.tools_path)
        self._db = DBStore(config.registry.db_path)
        self._vector = VectorStore(config.registry.vector_path)

    async def initialize(self):
        await self._db.initialize()

    async def close(self):
        await self._db.close()
        self._vector.close()

    async def add_tool(self, record: ToolRecord) -> None:
        """添加工具到三层存储。"""
        self._file_store.save(record)
        await self._db.insert_tool(record)
        self._vector.add(
            tool_id=record.id,
            name=record.name,
            description=record.meta.description,
            category=record.category,
        )

    async def get_tool(self, tool_id: str) -> ToolRecord | None:
        """通过 ID 获取完整工具记录（含代码）。"""
        db_record = await self._db.get_tool(tool_id)
        if not db_record:
            return None
        try:
            return self._file_store.load(db_record["name"], db_record["category"])
        except FileNotFoundError:
            return None

    async def search(self, query: str, top_k: int = 5) -> list[ToolRecord]:
        """语义搜索工具，返回按信任链优先度排序的结果。"""
        vector_results = self._vector.search(query, top_k=top_k)
        if not vector_results:
            return []

        records = []
        for vr in vector_results:
            db_record = await self._db.get_tool(vr["tool_id"])
            if db_record and db_record["status"] == "active":
                try:
                    full = self._file_store.load(db_record["name"], db_record["category"])
                    records.append(full)
                except FileNotFoundError:
                    continue

        _priority = {ToolSource.VERIFIED: 3, ToolSource.BUILTIN: 2, ToolSource.AUTO: 1}
        records.sort(key=lambda r: _priority.get(r.source, 0), reverse=True)
        return records[:top_k]

    async def log_execution(
        self,
        tool_id: str,
        task_id: str,
        success: bool,
        execution_time_ms: int,
        sandbox_id: str = "",
        error: str = "",
    ) -> None:
        """记录工具调用。"""
        record = ExecutionRecord(
            tool_id=tool_id,
            task_id=task_id,
            success=success,
            execution_time_ms=execution_time_ms,
            sandbox_id=sandbox_id,
            error_message=error,
        )
        await self._db.log_execution(record)

    async def get_tool_stats(self, tool_id: str) -> dict:
        """获取工具的调用统计。"""
        return await self._db.get_tool_stats(tool_id)

    async def mark_suspicious(self, tool_id: str, reason: str) -> None:
        """将工具标记为可疑。"""
        await self._db.update_tool_status(tool_id, ToolStatus.SUSPICIOUS)
        await self._db.log_security_event(tool_id, "marked_suspicious", reason)
