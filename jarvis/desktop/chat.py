"""Owns desktop sessions and the context sent to the selected backend."""
from pathlib import Path
import json
import re
import sqlite3
from uuid import uuid4

from .backend import ModelBackend
from .identity import CORE_IDENTITY
from .memory import DesktopMemory, SCHEMA, note_key, topic_match, topic_terms

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "desktop.sqlite3"
SYSTEM = {
    "role": "system",
    "content": (
        CORE_IDENTITY + "\n\nAnswer directly and naturally. "
        "Follow the user's requested format, check your conclusion for contradictions, and give only "
        "the explanation the user needs. Use ordinary assumptions for ordinary questions. "
        "If an uncertainty matters, explain it plainly and offer a useful next step. "
        "Ground statements about current files, actions, runtime, and memory in the information available. "
        "Pasted logs and saved context are supplied by the user. Earlier replies may be mistaken and "
        "cannot establish that something happened. Acknowledge and correct mistakes plainly. "
        "A configuration path alone cannot establish that a file exists or was used. "
        "Desktop stores persistent notes and includes selected notes in prompts. Flab can manage them "
        "in the Memory sidebar. Desktop handles explicit save requests such as 'Remember that ...' "
        "before generation and reports the result itself. Generated text cannot commit a memory. "
        "Recall from the transcript does not establish that a note was saved. "
        "Use evidence labels only when the user asks for them. Reserve VERIFIED for evidence supplied by the application."
    ),
}
HISTORY_SCHEMA = """
CREATE VIRTUAL TABLE desktop_history_search USING fts5(content);
INSERT INTO desktop_history_search(rowid,content)
SELECT id,content FROM messages WHERE role='user';
CREATE TRIGGER desktop_history_insert AFTER INSERT ON messages WHEN new.role='user' BEGIN
    INSERT INTO desktop_history_search(rowid,content) VALUES(new.id,new.content);
END;
CREATE TRIGGER desktop_history_delete AFTER DELETE ON messages WHEN old.role='user' BEGIN
    DELETE FROM desktop_history_search WHERE rowid=old.id;
END;
"""
CONTEXT_SCHEMA = """
CREATE TABLE desktop_context (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    archived_through INTEGER NOT NULL CHECK (archived_through >= 0)
);
INSERT INTO desktop_context VALUES (1, 0);
"""
NAME_REQUEST = re.compile(
    r"(?:please\s+)?save my name\s*\(\s*([^()\r\n]+?)\s*\)"
    r"(?:\s+in (?:your )?memor(?:y|ies))?[.!]?"
    r"(?:\s+i want you to remember when i reboot and start a new chat with you[.!]?)?",
    re.I,
)
NAME_STATEMENT = re.compile(
    r"(?:please\s+)?remember (?:that )?my name is ([^\r\n.!?]+)[.!]?",
    re.I,
)
NOTE_REQUEST = re.compile(
    r"(?:please\s+)?(?:remember that\s+|(?:remember|save (?:this(?: to memory)?|to memory))\s*:\s*)"
    r"([^\r\n]+)",
    re.I,
)


def memory_request(content):
    name = NAME_REQUEST.fullmatch(content.strip()) or NAME_STATEMENT.fullmatch(content.strip())
    if name:
        return "User's name", f"The user's name is {name[1].strip()}.", "standing"
    note = NOTE_REQUEST.fullmatch(content.strip())
    if note and not content.rstrip().endswith("?"):
        fact = note[1].strip()
        return fact[:80].rstrip(), fact, "relevant"
    return None


class ChatService:
    def __init__(self, backend: ModelBackend, path=DB_PATH):
        self.backend = backend
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        version = self.db.execute("PRAGMA user_version").fetchone()[0]
        if version == 0:
            self.db.executescript("""
                BEGIN;
                CREATE TABLE chats (
                    id TEXT PRIMARY KEY, title TEXT NOT NULL DEFAULT 'New chat',
                    model TEXT NOT NULL, draft TEXT NOT NULL DEFAULT '',
                    updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE messages (
                    id INTEGER PRIMARY KEY, chat_id TEXT NOT NULL REFERENCES chats(id),
                    role TEXT NOT NULL, content TEXT NOT NULL, model TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'complete'
                );
                CREATE INDEX messages_chat ON messages(chat_id, id);
                PRAGMA user_version = 1;
                COMMIT;
            """)
            version = 1
        if version == 1:
            self.db.executescript("BEGIN IMMEDIATE;\n" + SCHEMA + "\nPRAGMA user_version = 2; COMMIT;")
            version = 2
        if version == 2:
            self.db.executescript("BEGIN IMMEDIATE;\n" + HISTORY_SCHEMA + "\nPRAGMA user_version = 3; COMMIT;")
            version = 3
        if version == 3:
            self.db.executescript("BEGIN IMMEDIATE;\n" + CONTEXT_SCHEMA + "\nPRAGMA user_version = 4; COMMIT;")
            version = 4
        if version == 4:
            self.db.executescript("""
                BEGIN IMMEDIATE;
                ALTER TABLE chats ADD COLUMN hidden INTEGER NOT NULL DEFAULT 0 CHECK (hidden IN (0, 1));
                PRAGMA user_version = 5;
                COMMIT;
            """)
            version = 5
        if version != 5:
            self.db.close()
            raise RuntimeError("This chat database requires a newer version of Jarvis Desktop.")
        self.memory = DesktopMemory(self.db)

    def chats(self, include_hidden=False):
        return self.db.execute(
            "SELECT * FROM chats WHERE hidden=0 OR ? ORDER BY updated DESC, rowid DESC",
            (include_hidden,),
        ).fetchall()

    def set_chat_hidden(self, chat_id, hidden):
        with self.db:
            self.db.execute("UPDATE chats SET hidden=? WHERE id=?", (hidden, chat_id))

    def rename_chat(self, chat_id, title):
        title = title.strip()
        if not title:
            raise ValueError("Enter a chat title.")
        with self.db:
            self.db.execute("UPDATE chats SET title=? WHERE id=?", (title, chat_id))

    def create(self, model):
        chat_id = uuid4().hex
        with self.db:
            self.db.execute("INSERT INTO chats(id,model) VALUES (?,?)", (chat_id, model))
        return chat_id

    def select_model(self, chat_id, model):
        with self.db:
            self.db.execute("UPDATE chats SET model=? WHERE id=?", (model, chat_id))

    def save_draft(self, chat_id, draft):
        with self.db:
            self.db.execute("UPDATE chats SET draft=? WHERE id=?", (draft, chat_id))

    def messages(self, chat_id):
        return self.db.execute("""
            SELECT role, content, model, status,
                id <= (SELECT archived_through FROM desktop_context WHERE id=1) AS archived
            FROM messages WHERE chat_id=? ORDER BY id
        """, (chat_id,)).fetchall()

    def _record_request(self, chat_id, content):
        title = " ".join(content.split())
        title = title[:56] + ("…" if len(title) > 56 else "")
        with self.db:
            self.db.execute("INSERT INTO messages(chat_id,role,content) VALUES (?,'user',?)",
                            (chat_id, content))
            self.db.execute("""
                UPDATE chats SET draft='', updated=CURRENT_TIMESTAMP,
                title=CASE WHEN title='New chat' AND
                    (SELECT count(*) FROM messages WHERE chat_id=chats.id)=1 THEN ? ELSE title END
                WHERE id=?
            """, (title, chat_id))

    def save_requested_memory(self, chat_id, content, request):
        self._record_request(chat_id, content)
        try:
            self.memory.save(*request, chat_id)
        except (ValueError, sqlite3.Error) as error:
            reply = f"Memory save failed. {error}"
            saved = False
        else:
            reply = f"Saved to Memory: {request[1]}"
            saved = True
        self.finish(chat_id, reply, "", "complete")
        return saved

    def begin(self, chat_id, content):
        self._record_request(chat_id, content)
        messages = [row for row in self.messages(chat_id) if not row["archived"]]
        user_messages = [row["content"] for row in messages if row["role"] == "user"]
        context = self.memory.prompt(content, user_messages)
        context += self.history_prompt(chat_id, content, (*user_messages, *self.memory.included_text))
        system = {**SYSTEM, "content": SYSTEM["content"] + context}
        return [system, *(
            {"role": row["role"], "content": row["content"]}
            for row in messages
            if row["content"] and (row["role"] != "assistant" or row["status"] == "complete")
        )]

    def history_prompt(self, chat_id, content, already_in_context=()):
        # Other chats are reference material for recall requests, not ambient context.
        recall = r"\b(?:remember|recall|memory|last time|earlier chats?|previous chats?)\b"
        if not re.search(recall, content, re.I):
            return ""
        terms = topic_terms(re.sub(recall, "", content, flags=re.I))[-16:]
        if not terms:
            return ""
        expression = " OR ".join(f'"{term}"' for term in terms)
        seen = {note_key(text) for text in already_in_context}
        superseded = {
            (row["source_chat"], note_key(row["content"]))
            for row in self.db.execute("SELECT source_chat, content FROM desktop_memory_revisions")
        }
        lines = []
        for row in self.db.execute("""
            SELECT m.chat_id, m.content FROM desktop_history_search h
            JOIN messages m ON m.id=h.rowid
            JOIN chats c ON c.id=m.chat_id
            WHERE desktop_history_search MATCH ? AND m.chat_id<>? AND m.role='user' AND c.hidden=0
                AND m.id > (SELECT archived_through FROM desktop_context WHERE id=1)
            ORDER BY rank, m.id DESC
        """, (expression, chat_id)):
            key = note_key(row["content"])
            if key in seen or (row["chat_id"], key) in superseded:
                continue
            excerpt = row["content"][:240]
            if not topic_match(terms, excerpt):
                continue
            seen.add(key)
            lines.append(json.dumps(excerpt, ensure_ascii=False) + "\n")
            if len(lines) == 3:
                break
        if not lines:
            return ""
        block = "\n\nEarlier user messages are historical context. Follow the current request and newer corrections.\n"
        for line in lines:
            if len((block + line).encode("utf-8")) <= 900:
                block += line
        return block

    def finish(self, chat_id, content, model, status):
        with self.db:
            self.db.execute("""
                INSERT INTO messages(chat_id,role,content,model,status)
                VALUES (?,'assistant',?,?,?)
            """, (chat_id, content, model, status))

