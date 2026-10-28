"""Persistance des chunks + recherche vectorielle (pgvector, distance cosinus)."""
import psycopg

from app.config import settings
from app.rag.chunker import Chunk


def _vec(v: list[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in v) + "]"


class ChunkStore:
    def __init__(self, dsn: str | None = None):
        self.dsn = dsn or settings.postgres_dsn

    def replace_repo(self, repo_name: str, git_url: str | None,
                     chunks: list[Chunk], vectors: list[list[float]]) -> int:
        """Réindexation complète et atomique d'un dépôt (tout ou rien)."""
        with psycopg.connect(self.dsn) as conn:
            repo_id = conn.execute(
                """INSERT INTO repositories(name, git_url, indexed_at) VALUES (%s, %s, now())
                   ON CONFLICT (name) DO UPDATE SET git_url = EXCLUDED.git_url, indexed_at = now()
                   RETURNING id""",
                (repo_name, git_url),
            ).fetchone()[0]
            conn.execute("DELETE FROM chunks WHERE repo_id = %s", (repo_id,))
            with conn.cursor() as cur:
                cur.executemany(
                    """INSERT INTO chunks(repo_id, file, kind, symbol, language,
                                          start_line, end_line, content, embedding)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::vector)""",
                    [
                        (repo_id, c.file, c.kind, c.symbol, c.language,
                         c.start_line, c.end_line, c.content, _vec(v))
                        for c, v in zip(chunks, vectors, strict=True)
                    ],
                )
        return len(chunks)

    def search(self, repo_name: str, vector: list[float], limit: int) -> list[dict]:
        with psycopg.connect(self.dsn) as conn:
            rows = conn.execute(
                """SELECT c.file, c.kind, c.symbol, c.language, c.start_line, c.end_line,
                          c.content, 1 - (c.embedding <=> %s::vector) AS score
                   FROM chunks c JOIN repositories r ON r.id = c.repo_id
                   WHERE r.name = %s
                   ORDER BY c.embedding <=> %s::vector
                   LIMIT %s""",
                (_vec(vector), repo_name, _vec(vector), limit),
            ).fetchall()
        keys = ("file", "kind", "symbol", "language", "start_line", "end_line", "content", "score")
        return [dict(zip(keys, r)) for r in rows]

    def stats(self, repo_name: str) -> dict | None:
        with psycopg.connect(self.dsn) as conn:
            row = conn.execute(
                """SELECT r.git_url, r.indexed_at, count(c.id), count(DISTINCT c.file)
                   FROM repositories r LEFT JOIN chunks c ON c.repo_id = r.id
                   WHERE r.name = %s GROUP BY r.id""",
                (repo_name,),
            ).fetchone()
        if row is None:
            return None
        return {"repo_name": repo_name, "git_url": row[0], "indexed_at": row[1],
                "chunks": row[2], "files": row[3]}
