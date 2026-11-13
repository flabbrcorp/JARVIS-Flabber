"""test_memory.py - Phase 1 checks. Run: python test_memory.py

Uses a temporary directory, so it never touches your real memory.db.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import memory

passed = 0


def check(name, condition):
    global passed
    if not condition:
        print(f"FAIL: {name}")
        sys.exit(1)
    passed += 1
    print(f"  ok  {name}")


with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    db = str(tmp / "test.db")

    print("episodes")
    ids = [
        memory.log_episode("s1", "user", "hello there", db_path=db),
        memory.log_episode("s1", "assistant", "hi!", db_path=db),
        memory.log_episode("s1", "user", "I run a 3090", db_path=db),
        memory.log_episode("s2", "user", "other session", db_path=db),
    ]
    check("ids increase", ids == sorted(ids) and len(set(ids)) == 4)
    recent = memory.get_recent_episodes("s1", n=2, db_path=db)
    check("returns last n, oldest first",
          [e["content"] for e in recent] == ["hi!", "I run a 3090"])
    check("sessions are isolated",
          len(memory.get_recent_episodes("s2", db_path=db)) == 1)
    check("unknown session is empty",
          memory.get_recent_episodes("nope", db_path=db) == [])

    print("memories + keyword search")
    m1 = memory.add_memory("User runs the model on an RTX 3090", "fact", 7,
                           source_episode=ids[2], db_path=db)
    m2 = memory.add_memory("User prefers terse answers", "preference", 8, db_path=db)
    m3 = memory.add_memory("User's dog is named Biscuit", "fact", 3, db_path=db)
    hits = memory.search_keyword("what GPU... RTX 3090?", db_path=db)
    check("finds the matching memory", hits and hits[0]["id"] == m1)
    check("returns metadata", hits[0]["type"] == "fact" and hits[0]["importance"] == 7)
    check("no match returns empty", memory.search_keyword("zebra", db_path=db) == [])
    check("empty query returns empty", memory.search_keyword("   ", db_path=db) == [])
    nasty = memory.search_keyword('"dog" AND (name: OR NOT *', db_path=db)
    check("special characters don't crash", any(h["id"] == m3 for h in nasty))
    check("limit is respected",
          len(memory.search_keyword("user", limit=2, db_path=db)) == 2)

    print("FTS stays in sync")
    with memory._connect(db) as conn:
        conn.execute("UPDATE memories SET archived = 1 WHERE id = ?", (m2,))
    check("archived memories are hidden",
          all(h["id"] != m2 for h in memory.search_keyword("terse", db_path=db)))
    with memory._connect(db) as conn:
        conn.execute("UPDATE memories SET superseded_by = ? WHERE id = ?", (m1, m3))
    check("superseded memories are hidden",
          all(h["id"] != m3 for h in memory.search_keyword("Biscuit", db_path=db)))
    with memory._connect(db) as conn:
        conn.execute("UPDATE memories SET text = 'User runs a 4090' WHERE id = ?", (m1,))
    check("text updates reindex",
          memory.search_keyword("4090", db_path=db)
          and not memory.search_keyword("3090", db_path=db))

    print("validation")
    for bad in [dict(text="  "), dict(text="x", importance=11)]:
        try:
            memory.add_memory(db_path=db, **bad)
            check(f"rejects {bad}", False)
        except ValueError:
            check(f"rejects {bad}", True)

    print("migration")
    j1, j2 = tmp / "core.json", tmp / "notes.json"
    j1.write_text(json.dumps({"name": "Sam", "prefs": {"tone": "casual"}}))
    j2.write_text(json.dumps(["likes tea", {"text": "works nights"}]))
    mdb = str(tmp / "migrated.db")
    cmd = [sys.executable, "migrate_json.py", str(j1), str(j2), "--db", mdb]
    out = subprocess.run(cmd, capture_output=True, text=True)
    check("migration exits cleanly", out.returncode == 0)
    with memory._connect(mdb) as conn:
        rows = conn.execute("SELECT * FROM memories").fetchall()
    texts = {r["text"] for r in rows}
    check("all 4 entries imported", len(rows) == 4)
    check("flattening works",
          {"name: Sam", "prefs > tone: casual", "likes tea", "works nights"} == texts)
    check("legacy defaults applied",
          all(r["type"] == "legacy" and r["importance"] == 5
              and r["confidence"] == 0.5 for r in rows))
    check("originals untouched", json.loads(j1.read_text())["name"] == "Sam")
    check("backups created", len(list(tmp.glob("*.json.bak-*"))) == 2)
    subprocess.run(cmd, capture_output=True, text=True)
    with memory._connect(mdb) as conn:
        n = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    check("re-running doesn't duplicate", n == 4)

print(f"\nAll {passed} checks passed.")
