"""Retrieval module — scored search over SQLite-backed memories."""

import sqlite3
import re
from typing import List, Dict, Any, Optional


def _to_fts_query(query: str) -> str:
    """Turn free text into a safe FTS5 query: quoted tokens joined by OR."""
    tokens = re.findall(r"\w+", query)
    return " OR ".join(f'"{t}"' for t in tokens)


def init_db(db_path: Optional[str] = None) -> None:
    """Ensure the memory database tables and FTS index exist."""
    import jarvis_memory as mm
    mm.init_db(db_path)


def scored_search(query: str, limit: int = 8, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """BM25 keyword search over active memories (not archived, not superseded).

    Returns a list of dicts, best match first. Each includes a 'score' where
    higher is better. This is the independent scored_search implementation
    used by the memory pipeline test.

    Args:
        query: The search text.
        limit: Maximum number of results to return.
        db_path: Path to the SQLite database. Uses MEMORY_DB env var if not
            provided.

    Returns:
        A list of dicts, each containing memory fields plus a 'score' key.
    """
    fts_query = _to_fts_query(query)
    if not fts_query:
        return []

    init_db(db_path)
    import jarvis_memory as mm

    with mm._connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT m.*, -bm25(memories_fts) AS score
            FROM memories_fts
            JOIN memories m ON m.id = memories_fts.rowid
            WHERE memories_fts MATCH ?
              AND m.archived = 0
              AND m.superseded_by IS NULL
            ORDER BY bm25(memories_fts)
            LIMIT ?
            """,
            (fts_query, limit),
        ).fetchall()
        return [dict(r) for r in rows]