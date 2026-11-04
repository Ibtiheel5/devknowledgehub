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
                     chunks: list[Chunk], vectors: list[list[float]],
                     commit_sha: str | None = None) -> int:
        """Réindexation complète et atomique d'un dépôt (tout ou rien)."""
        with psycopg.connect(self.dsn) as conn:
            repo_id = conn.execute(
                """INSERT INTO repositories(name, git_url, indexed_at, commit_sha)
                   VALUES (%s, %s, now(), %s)
                   ON CONFLICT (name) DO UPDATE
                       SET git_url = COALESCE(EXCLUDED.git_url, repositories.git_url),
                           commit_sha = COALESCE(EXCLUDED.commit_sha, repositories.commit_sha),
                           indexed_at = now()
                   RETURNING id""",
                (repo_name, git_url, commit_sha),
            ).fetchone()[0]
            conn.execute("DELETE FROM chunks WHERE repo_id = %s", (repo_id,))
            with conn.cursor() as cur:
                cur.executemany(
                    """INSERT INTO chunks(repo_id, file, kind, symbol, language,
                                          start_line, end_line, content, embedding, commit_sha)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::vector,%s)""",
                    [
                        (repo_id, c.file, c.kind, c.symbol, c.language,
                         c.start_line, c.end_line, c.content, _vec(v), commit_sha)
                        for c, v in zip(chunks, vectors, strict=True)
                    ],
                )
        return len(chunks)

    def search(self, repo_name: str, vector: list[float], limit: int,
               kinds: tuple[str, ...] | None = None) -> list[dict]:
        where = "r.name = %s"
        params: list = [_vec(vector), repo_name]
        if kinds:
            where += " AND c.kind = ANY(%s)"
            params.append(list(kinds))
        params.extend([_vec(vector), limit])
        with psycopg.connect(self.dsn) as conn:
            rows = conn.execute(
                f"""SELECT c.file, c.kind, c.symbol, c.language, c.start_line, c.end_line,
                           c.content, 1 - (c.embedding <=> %s::vector) AS score
                    FROM chunks c JOIN repositories r ON r.id = c.repo_id
                    WHERE {where}
                    ORDER BY c.embedding <=> %s::vector
                    LIMIT %s""",
                params,
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
