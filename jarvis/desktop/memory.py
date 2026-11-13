"""User-saved notes and lightweight retrieval for desktop conversations."""
import json
import re
from time import perf_counter

MEMORY_BUDGET_BYTES = 1600
ENTRY_BUDGET_BYTES = 300
STOP_WORDS = frozenset(
    "a an and are as at be by can could did do does for from had has have how i in is it "
    "for me my of on or our please recall remember should tell that the their them these this to use was we "
    "were what when where which who why will with would you your".split()
)
PROMPT_HEADER = (
    "\n\nSaved notes contain user-supplied context, including any quoted claims. "
    "They carry no independent verification. Follow the current user's corrections. "
    "If conflicting notes matter, ask which applies.\n"
)


def topic_terms(text):
    return tuple(dict.fromkeys(
        word for word in re.findall(r"[^\W_]+", text.lower())
        if 2 <= len(word) <= 64 and word not in STOP_WORDS
    ))


def topic_match(terms, text):
    # A single keyword suffices only for an explicitly narrow query.
    return bool(terms) and len(set(terms).intersection(topic_terms(text))) >= min(2, len(terms))


def note_key(text):
    return " ".join(text.casefold().split()).strip(".!?")


SCHEMA = """
CREATE TABLE IF NOT EXISTS desktop_memories (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    scope TEXT NOT NULL CHECK (scope IN ('relevant', 'standing')),
    source_chat TEXT REFERENCES chats(id),
    revision INTEGER NOT NULL DEFAULT 1,
    updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS desktop_memory_revisions (
    memory_id INTEGER NOT NULL REFERENCES desktop_memories(id) ON DELETE CASCADE,
    revision INTEGER NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    scope TEXT NOT NULL,
    source_chat TEXT REFERENCES chats(id),
    updated TEXT NOT NULL,
    PRIMARY KEY (memory_id, revision)
);
CREATE VIRTUAL TABLE IF NOT EXISTS desktop_memory_search USING fts5(
    title, content, content='desktop_memories', content_rowid='id'
);
CREATE TRIGGER IF NOT EXISTS desktop_memory_insert AFTER INSERT ON desktop_memories BEGIN
    INSERT INTO desktop_memory_search(rowid, title, content) VALUES (new.id, new.title, new.content);
END;
CREATE TRIGGER IF NOT EXISTS desktop_memory_delete AFTER DELETE ON desktop_memories BEGIN
    INSERT INTO desktop_memory_search(desktop_memory_search, rowid, title, content)
    VALUES ('delete', old.id, old.title, old.content);
END;
CREATE TRIGGER IF NOT EXISTS desktop_memory_update AFTER UPDATE ON desktop_memories BEGIN
    INSERT INTO desktop_memory_search(desktop_memory_search, rowid, title, content)
    VALUES ('delete', old.id, old.title, old.content);
    INSERT INTO desktop_memory_search(rowid, title, content) VALUES (new.id, new.title, new.content);
END;
CREATE INDEX IF NOT EXISTS desktop_memory_scope ON desktop_memories(scope, updated);
"""


def _line(title, content):
    return json.dumps({"title": title, "memory": content}, ensure_ascii=False) + "\n"


class DesktopMemory:
    def __init__(self, db):
        self.db = db
        self.used = ()
        self.included_text = ()
        self.lookup_ms = 0.0
        self.prompt_bytes = 0

    def list(self):
        return self.db.execute("""
            SELECT m.*, c.title AS source_title
            FROM desktop_memories m LEFT JOIN chats c ON c.id=m.source_chat
            ORDER BY m.updated DESC, m.id DESC
        """).fetchall()

    def save(self, title, content, scope, source_chat, memory_id=None):
        title, content = title.strip(), content.strip()
        if not title or not content:
            raise ValueError("Enter a title and a memory.")
        if scope not in ("relevant", "standing"):
            raise ValueError("Choose a memory scope.")
        if len(_line(title, content).encode("utf-8")) > ENTRY_BUDGET_BYTES:
            raise ValueError("Shorten the title or memory. A short sentence works best.")
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            existing = self.db.execute("SELECT id, title FROM desktop_memories").fetchall()
            topic = note_key(title)
            same_title = [row["id"] for row in existing if note_key(row["title"]) == topic]
            if same_title and memory_id not in same_title:
                raise ValueError("A memory already has that title. Edit it or give the new memory a distinct title.")
            if memory_id is None:
                self.db.execute("""
                    INSERT INTO desktop_memories(title,content,scope,source_chat) VALUES (?,?,?,?)
                """, (title, content, scope, source_chat))
            else:
                previous = self.db.execute("""
                    INSERT INTO desktop_memory_revisions
                    SELECT id,revision,title,content,scope,source_chat,updated
                    FROM desktop_memories WHERE id=?
                """, (memory_id,))
                if previous.rowcount != 1:
                    raise ValueError("This memory has already been removed.")
                self.db.execute("""
                    UPDATE desktop_memories SET title=?, content=?, scope=?, source_chat=?,
                        revision=revision+1, updated=CURRENT_TIMESTAMP WHERE id=?
                """, (title, content, scope, source_chat, memory_id))

    def forget(self, memory_id):
        with self.db:
            self.db.execute("DELETE FROM desktop_memories WHERE id=?", (memory_id,))

    def prompt(self, query, current_user_messages=()):
        started = perf_counter()
        terms = topic_terms(query)[-24:]
        rows = self.db.execute("""
            SELECT id, title, content, scope, source_chat, revision, updated
            FROM desktop_memories ORDER BY updated DESC, id DESC
        """).fetchall()
        by_id = {row["id"]: row for row in rows}
        topics = {}
        for row in rows:
            topics.setdefault(note_key(row["title"]), set()).add(note_key(row["content"]))
        standing = [row for row in rows if row["scope"] == "standing"][:8]
        matches = []
        if terms:
            expression = " OR ".join(f'"{term}"' for term in terms)
            for hit in self.db.execute("""
                SELECT m.id FROM desktop_memory_search JOIN desktop_memories m
                    ON m.id=desktop_memory_search.rowid
                WHERE desktop_memory_search MATCH ? AND m.scope='relevant'
                ORDER BY rank, m.updated DESC, m.id DESC
            """, (expression,)):
                row = by_id.get(hit["id"])
                if row is not None and topic_match(terms, f'{row["title"]} {row["content"]}'):
                    matches.append(row)
                    if len(matches) == 8:
                        break

        remaining = MEMORY_BUDGET_BYTES - len(PROMPT_HEADER.encode("utf-8"))
        lines, titles, included = [], [], []
        seen = {note_key(text) for text in current_user_messages}
        conflicts = set()
        for row in [*standing[:1], *matches, *standing[1:]]:
            key = note_key(row["content"])
            topic = note_key(row["title"])
            if len(topics[topic]) > 1:
                if topic in conflicts:
                    continue
                entry = {"title": row["title"], "conflict": "Multiple saved versions. Values withheld."}
            elif key in seen:
                continue
            else:
                entry = {
                    "title": row["title"], "memory": row["content"], "scope": row["scope"],
                    "source_chat_id": row["source_chat"],
                    "revision": row["revision"], "updated_utc": row["updated"],
                }
            line = json.dumps(entry, ensure_ascii=False) + "\n"
            size = len(line.encode("utf-8"))
            if size > remaining:
                continue
            lines.append(line)
            remaining -= size
            if "conflict" in entry:
                conflicts.add(topic)
            else:
                seen.add(key)
                included.append(row["content"])
                titles.append(row["title"])
        block = PROMPT_HEADER + "".join(lines) if lines else ""
        self.used = tuple(titles)
        self.included_text = tuple(included)
        self.lookup_ms = (perf_counter() - started) * 1000
        self.prompt_bytes = len(block.encode("utf-8"))
        return block
