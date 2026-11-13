"""core_memory.py - Phase 2: small always-in-prompt memory tier.

Own table in the same database as memory.py. Standard library only.
"""

import time

import memory

MAX_CHARS = 3000  # total of all keys and values, hard cap

_SCHEMA = ("CREATE TABLE IF NOT EXISTS core_memory ("
           "key TEXT PRIMARY KEY, value TEXT NOT NULL, updated REAL NOT NULL)")


class CoreMemoryFull(Exception):
    """Raised when set_core would push total size beyond MAX_CHARS."""


def _ensure_table(conn):
    conn.execute(_SCHEMA)


def set_core(key, value, db_path=None):
    """Insert or replace a core entry.

    Raises CoreMemoryFull if the total size after the change would exceed
    MAX_CHARS (data left unchanged). Raises ValueError on empty or
    whitespace-only keys or values. Returns the update timestamp.
    """
    if not isinstance(key, str) or not key.strip():
        raise ValueError("key must be a non-empty, non-whitespace string")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("value must be a non-empty, non-whitespace string")
    new_size = len(key) + len(value)
    with memory._connect(db_path) as conn:
        _ensure_table(conn)
        existing = conn.execute("SELECT value FROM core_memory WHERE key = ?",
                                (key,)).fetchone()
        current = conn.execute("SELECT COALESCE(SUM(LENGTH(key) + LENGTH(value)), 0) "
                                "FROM core_memory").fetchone()[0]
        if existing is not None:
            total_after = current - (len(key) + len(existing["value"])) + new_size
        else:
            total_after = current + new_size
        if total_after > MAX_CHARS:
            raise CoreMemoryFull(
                f"set_core would exceed {MAX_CHARS} chars (total would be {total_after})")
        updated = time.time()
        conn.execute(
            "INSERT INTO core_memory (key, value, updated) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
            "updated = excluded.updated",
            (key, value, updated))
    return updated


def delete_core(key, db_path=None):
    """Delete a core entry. Returns True if something was deleted."""
    with memory._connect(db_path) as conn:
        _ensure_table(conn)
        cur = conn.execute("DELETE FROM core_memory WHERE key = ?", (key,))
        return cur.rowcount > 0


def get_core_block(db_path=None):
    """Return the text block for the prompt, or "" if empty.

    One "key: value" line per entry, sorted by key.
    """
    with memory._connect(db_path) as conn:
        _ensure_table(conn)
        rows = conn.execute(
            "SELECT key, value FROM core_memory ORDER BY key").fetchall()
    return "".join(f"{r['key']}: {r['value']}\n" for r in rows)
