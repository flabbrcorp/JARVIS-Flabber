"""jarvis_resume.py - build a short "where we left off" brief for a new chat.

Read-only and standard library only. It never writes to memory.md or the database.
Use build_resume_brief() and put the returned text at the top of the model's context.
"""
import pathlib
import sqlite3

ROOT = pathlib.Path(__file__).resolve().parent
DEFAULT_MD = ROOT / "memory.md"
DEFAULT_DB = ROOT / "memory" / "memory.db"


def _clip(text, n):
    """Collapse whitespace and cut to n characters."""
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[: n - 3] + "..."


def _read_sections(md_path):
    """Return {heading: [non-empty lines]} for '## ' headings. Missing file -> {}."""
    try:
        text = pathlib.Path(md_path).read_text(encoding="utf-8")
    except OSError:
        return {}
    sections, name = {}, None
    for line in text.splitlines():
        if line.startswith("## "):
            name = line[3:].strip()
            sections[name] = []
        elif name is not None and line.strip():
            sections[name].append(line.rstrip())
    return sections


def _connect_ro(db_path):
    """Open the database read-only, or return None if it does not exist."""
    p = pathlib.Path(db_path)
    if not p.is_file():
        return None
    conn = sqlite3.connect(p.resolve().as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _last_session_turns(db_path, exclude_session, n):
    """Last n turns of the most recent session other than exclude_session."""
    conn = _connect_ro(db_path)
    if conn is None:
        return []
    try:
        row = conn.execute(
            "SELECT session_id FROM episodes WHERE session_id != ? "
            "ORDER BY id DESC LIMIT 1",
            (exclude_session or "",),
        ).fetchone()
        if row is None:
            return []
        rows = conn.execute(
            "SELECT role, content FROM episodes WHERE session_id = ? "
            "ORDER BY id DESC LIMIT ?",
            (row["session_id"], n),
        ).fetchall()
        return [(r["role"], r["content"]) for r in reversed(rows)]
    except sqlite3.Error:
        return []
    finally:
        conn.close()


def _top_memories(db_path, n):
    """Most important active memories, newest first among equals."""
    conn = _connect_ro(db_path)
    if conn is None:
        return []
    try:
        rows = conn.execute(
            "SELECT text FROM memories WHERE archived = 0 AND superseded_by IS NULL "
            "ORDER BY importance DESC, COALESCE(last_used, created) DESC LIMIT ?",
            (n,),
        ).fetchall()
        return [r["text"] for r in rows]
    except sqlite3.Error:
        return []
    finally:
        conn.close()


def build_resume_brief(memory_md=None, db_path=None, current_session=None,
                       max_chars=1800, recent_turns=6, log_lines=5,
                       top_memories=5):
    """Return a short text block: where we left off, plus who the user is.

    Blocks are added in priority order and a block is skipped if it would push
    the total over max_chars, so the brief never grows past the limit.
    Returns "" if there is nothing to say.
    """
    sections = _read_sections(memory_md or DEFAULT_MD)
    db = db_path or DEFAULT_DB

    def pick(prefix):
        for name, lines in sections.items():
            if name.startswith(prefix):
                return lines
        return []

    blocks = []

    projects = [l for l in pick("Active Projects") if "(none" not in l.lower()]
    if projects:
        blocks.append("Active projects:\n" + "\n".join(_clip(l, 200) for l in projects))

    turns = _last_session_turns(db, current_session, recent_turns)
    if turns:
        lines = [f"- {role}: {_clip(content, 200)}" for role, content in turns]
        blocks.append("Last chat (most recent turns):\n" + "\n".join(lines))

    log = pick("Notes")[-log_lines:]
    if log:
        blocks.append("Recent notes:\n" + "\n".join(_clip(l, 300) for l in log))

    who = pick("The User")
    if who:
        blocks.append("Who you are talking to:\n" + "\n".join(_clip(l, 200) for l in who))

    rules = pick("Standing Rules")
    if rules:
        blocks.append("Standing rules:\n" + "\n".join(_clip(l, 200) for l in rules))

    mems = _top_memories(db, top_memories)
    if mems:
        blocks.append("Remembered facts:\n" + "\n".join(f"- {_clip(m, 200)}" for m in mems))

    out, used = [], 0
    for block in blocks:
        cost = len(block) + (2 if out else 0)
        if used + cost <= max_chars:
            out.append(block)
            used += cost
    return "\n\n".join(out)


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(build_resume_brief())
