"""memory.py - Phase 1: SQLite-backed memory for the local assistant.

Standard library only. One database file (default: memory.db, override with
the MEMORY_DB environment variable or the db_path argument).
"""

import os
import re
import sqlite3
import time
from contextlib import contextmanager

DEFAULT_DB = os.environ.get("MEMORY_DB", "memory.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS episodes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT    NOT NULL,
    ts         REAL    NOT NULL,
    role       TEXT    NOT NULL,
    content    TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_episodes_session ON episodes(session_id, id);

CREATE TABLE IF NOT EXISTS memories (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    text           TEXT    NOT NULL,
    type           TEXT    NOT NULL DEFAULT 'fact',
    importance     INTEGER NOT NULL DEFAULT 5,
    confidence     REAL    NOT NULL DEFAULT 0.5,
    created        REAL    NOT NULL,
    last_used      REAL,
    use_count      INTEGER NOT NULL DEFAULT 0,
    source_episode INTEGER REFERENCES episodes(id),
    superseded_by  INTEGER REFERENCES memories(id),
    archived       INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS lessons (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    trigger  TEXT NOT NULL,
    action   TEXT NOT NULL,
    ts       REAL NOT NULL,
    strength REAL NOT NULL DEFAULT 1.0
);

-- External-content FTS5 index over memories.text, kept in sync by triggers.
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    text, content='memories', content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
    INSERT INTO memories_fts(rowid, text) VALUES (new.id, new.text);
END;
CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, text)
    VALUES ('delete', old.id, old.text);
END;
CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE OF text ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, text)
    VALUES ('delete', old.id, old.text);
    INSERT INTO memories_fts(rowid, text) VALUES (new.id, new.text);
END;
"""


@contextmanager
def _connect(db_path=None):
    conn = sqlite3.connect(db_path or DEFAULT_DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path=None):
    """Create tables, indexes, FTS table and triggers if they don't exist."""
    with _connect(db_path) as conn:
        conn.executescript(SCHEMA)


def log_episode(session_id, role, content, db_path=None):
    """Append one conversation turn. Returns the new episode id."""
    init_db(db_path)
    with _connect(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO episodes (session_id, ts, role, content) VALUES (?, ?, ?, ?)",
            (session_id, time.time(), role, content),
        )
        return cur.lastrowid


def add_memory(text, type="fact", importance=5, source_episode=None,
               confidence=0.5, db_path=None):
    """Insert a memory. Returns the new memory id."""
    if not text or not text.strip():
        raise ValueError("memory text must not be empty")
    if not 1 <= importance <= 10:
        raise ValueError("importance must be between 1 and 10")
    init_db(db_path)
    with _connect(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO memories (text, type, importance, confidence, created, "
            "source_episode) VALUES (?, ?, ?, ?, ?, ?)",
            (text.strip(), type, importance, confidence, time.time(), source_episode),
        )
        return cur.lastrowid


def _to_fts_query(query):
    """Turn free text into a safe FTS5 query: quoted tokens joined by OR.

    Raw user text often contains characters (quotes, colons, hyphens, AND/NOT)
    that FTS5 treats as syntax and errors on. Quoting every token avoids that.
    """
    tokens = re.findall(r"\w+", query)
    return " OR ".join(f'"{t}"' for t in tokens)


def search_keyword(query, limit=8, db_path=None):
    """BM25 keyword search over active memories (not archived, not superseded).

    Returns a list of dicts, best match first. Each includes a 'score' where
    higher is better.
    """
    fts_query = _to_fts_query(query)
    if not fts_query:
        return []
    init_db(db_path)
    with _connect(db_path) as conn:
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


def get_recent_episodes(session_id, n=20, db_path=None):
    """Last n turns of a session, returned oldest to newest."""
    init_db(db_path)
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM episodes WHERE session_id = ? ORDER BY id DESC LIMIT ?",
            (session_id, n),
        ).fetchall()
        return [dict(r) for r in reversed(rows)]
