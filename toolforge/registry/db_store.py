"""SQLite 管理层 — 元数据查询、调用统计、安全审计。"""
import json
import uuid
import aiosqlite
from datetime import datetime
from pathlib import Path
from toolforge.registry.models import ToolMeta, ToolRecord, ToolSource, ToolStatus, ExecutionRecord


class DBStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def initialize(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS tools (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                version TEXT NOT NULL DEFAULT '0.1.0',
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'auto',
                status TEXT NOT NULL DEFAULT 'active',
                dependencies TEXT NOT NULL DEFAULT '[]',
                usage_example TEXT NOT NULL DEFAULT '',
                embedding_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS executions (
                id TEXT PRIMARY KEY,
                tool_id TEXT NOT NULL REFERENCES tools(id),
                task_id TEXT NOT NULL DEFAULT '',
                success INTEGER NOT NULL DEFAULT 1,
                execution_time_ms INTEGER NOT NULL DEFAULT 0,
                sandbox_id TEXT NOT NULL DEFAULT '',
                error_message TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS security_log (
                id TEXT PRIMARY KEY,
                tool_id TEXT REFERENCES tools(id),
                event_type TEXT NOT NULL,
                detail TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
        """)
        await self._conn.commit()

    async def close(self):
        if self._conn:
            await self._conn.close()

    async def _list_tables(self) -> list[str]:
        cursor = await self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        return [row[0] for row in await cursor.fetchall()]

    async def insert_tool(self, record: ToolRecord) -> None:
        await self._conn.execute(
            """INSERT OR REPLACE INTO tools
               (id, name, version, description, category, source, status,
                dependencies, usage_example, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record.id,
                record.name,
                record.meta.version,
                record.meta.description,
                record.category,
                record.source.value,
                record.meta.status.value,
                json.dumps(record.meta.dependencies),
                record.meta.usage_example,
                record.meta.created_at.isoformat(),
                record.meta.updated_at.isoformat(),
            ),
        )
        await self._conn.commit()

    async def get_tool(self, tool_id: str) -> dict | None:
        cursor = await self._conn.execute("SELECT * FROM tools WHERE id = ?", (tool_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_tool_by_name(self, name: str) -> dict | None:
        cursor = await self._conn.execute("SELECT * FROM tools WHERE name = ?", (name,))
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def search_tools(
        self,
        category: str | None = None,
        source: ToolSource | None = None,
        status: ToolStatus | None = None,
    ) -> list[dict]:
        query = "SELECT * FROM tools WHERE 1=1"
        params: list = []
        if category:
            query += " AND category = ?"
            params.append(category)
        if source:
            query += " AND source = ?"
            params.append(source.value)
        if status:
            query += " AND status = ?"
            params.append(status.value)
        else:
            query += " AND status = 'active'"
        cursor = await self._conn.execute(query, params)
        return [dict(row) for row in await cursor.fetchall()]

    async def update_tool_status(self, tool_id: str, status: ToolStatus) -> None:
        await self._conn.execute(
            "UPDATE tools SET status = ? WHERE id = ?",
            (status.value, tool_id),
        )
        await self._conn.commit()

    async def log_execution(self, record: ExecutionRecord) -> None:
        await self._conn.execute(
            """INSERT INTO executions (id, tool_id, task_id, success,
               execution_time_ms, sandbox_id, error_message, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record.id,
                record.tool_id,
                record.task_id,
                1 if record.success else 0,
                record.execution_time_ms,
                record.sandbox_id,
                record.error_message,
                record.created_at.isoformat(),
            ),
        )
        await self._conn.commit()

    async def get_tool_stats(self, tool_id: str) -> dict:
        cursor = await self._conn.execute(
            "SELECT COUNT(*) as total, "
            "SUM(CASE WHEN success THEN 1 ELSE 0 END) as successes "
            "FROM executions WHERE tool_id = ?",
            (tool_id,),
        )
        row = await cursor.fetchone()
        total = row["total"] or 0
        successes = row["successes"] or 0
        return {
            "total_calls": total,
            "success_rate": successes / total if total > 0 else 0.0,
        }

    async def log_security_event(self, tool_id: str, event_type: str, detail: str) -> None:
        await self._conn.execute(
            "INSERT INTO security_log (id, tool_id, event_type, detail, created_at) VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), tool_id, event_type, detail, datetime.now().isoformat()),
        )
        await self._conn.commit()
