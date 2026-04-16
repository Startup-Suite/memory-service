import logging
from datetime import datetime

import asyncpg
import numpy as np
from pgvector.asyncpg import register_vector

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS embeddings (
    entry_id     UUID PRIMARY KEY,
    embedding    vector({dim}) NOT NULL,
    workspace_id UUID,
    memory_type  TEXT NOT NULL,
    date         DATE NOT NULL,
    ingested_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_embeddings_workspace_id
    ON embeddings (workspace_id) WHERE workspace_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_embeddings_memory_type
    ON embeddings (memory_type);
CREATE INDEX IF NOT EXISTS idx_embeddings_date
    ON embeddings (date);
CREATE INDEX IF NOT EXISTS idx_embeddings_ingested_at
    ON embeddings (ingested_at);
"""


class VectorDB:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    @classmethod
    async def create(cls, database_url: str, dimension: int) -> "VectorDB":
        pool = await asyncpg.create_pool(
            database_url,
            min_size=2,
            max_size=10,
            init=register_vector,
        )
        async with pool.acquire() as conn:
            await conn.execute(SCHEMA_SQL.format(dim=dimension))
        logger.info("Database initialized (dimension=%d)", dimension)
        return cls(pool)

    async def close(self):
        await self.pool.close()

    async def upsert(self, entries: list[dict]):
        async with self.pool.acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO embeddings (entry_id, embedding, workspace_id, memory_type, date)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (entry_id) DO UPDATE SET
                    embedding = EXCLUDED.embedding,
                    workspace_id = EXCLUDED.workspace_id,
                    memory_type = EXCLUDED.memory_type,
                    date = EXCLUDED.date,
                    ingested_at = NOW()
                """,
                [
                    (
                        e["entry_id"],
                        e["embedding"],
                        e["workspace_id"],
                        e["memory_type"],
                        e["date"],
                    )
                    for e in entries
                ],
            )

    async def search(
        self,
        query_vector: np.ndarray,
        *,
        workspace_id: str | None = None,
        memory_type: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        conditions = []
        params: list = [query_vector, limit]
        param_idx = 3

        if workspace_id is not None:
            conditions.append(f"workspace_id = ${param_idx}")
            params.append(workspace_id)
            param_idx += 1

        if memory_type is not None:
            conditions.append(f"memory_type = ${param_idx}")
            params.append(memory_type)
            param_idx += 1

        if date_from is not None:
            conditions.append(f"date >= ${param_idx}")
            params.append(date_from)
            param_idx += 1

        if date_to is not None:
            conditions.append(f"date <= ${param_idx}")
            params.append(date_to)
            param_idx += 1

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        sql = f"""
            SELECT entry_id, 1 - (embedding <=> $1) AS score
            FROM embeddings
            {where}
            ORDER BY embedding <=> $1
            LIMIT $2
        """

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)

        return [{"entry_id": str(row["entry_id"]), "score": float(row["score"])} for row in rows]

    async def delete(self, entry_ids: list[str]) -> int:
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM embeddings WHERE entry_id = ANY($1::uuid[])",
                entry_ids,
            )
        return int(result.split()[-1])

    async def list_since(self, since: datetime) -> list[str]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT entry_id FROM embeddings WHERE ingested_at >= $1 ORDER BY ingested_at",
                since,
            )
        return [str(row["entry_id"]) for row in rows]
