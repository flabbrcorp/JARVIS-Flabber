"""test_retrieval.py - Phase 2 checks. Run: python test_retrieval.py

Uses a temporary database, so it never touches the real memory.db.
"""

import sys
import tempfile
from pathlib import Path

import memory
import retrieval

passed = 0


def check(name, condition):
    global passed
    if not condition:
        print(f"FAIL: {name}")
        sys.exit(1)
    passed += 1
    print(f"  ok  {name}")


NOW = 1_700_000_000.0  # injected clock: deterministic for all tests
DAY = 24 * 3600

with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    db = str(tmp / "test.db")
    memory.init_db(db_path=db)

    print("scored_search ranking")
    # Same text relevance; only recency differs.
    recent_id = memory.add_memory("User runs a local LLM nightly", db_path=db)
    old_id = memory.add_memory("User runs a local LLM nightly", db_path=db)
    with memory._connect(db) as conn:
        conn.execute("UPDATE memories SET created = ?, last_used = ? "
                     "WHERE id = ?", (NOW, NOW, recent_id))
        conn.execute("UPDATE memories SET created = ?, last_used = ? "
                     "WHERE id = ?", (NOW - 90 * DAY, NOW - 90 * DAY, old_id))
    hits = retrieval.scored_search("runs local LLM nightly", db_path=db, now=NOW)
    check("recent memory outranks equally relevant old one",
          len(hits) >= 2 and hits[0]["id"] == recent_id and hits[1]["id"] == old_id)
    check("final_score added and ordered",
          all("final_score" in h for h in hits)
          and hits[0]["final_score"] > hits[1]["final_score"])

    # Same age; importance decides.
    low_id = memory.add_memory("low importance note", importance=1, db_path=db)
    high_id = memory.add_memory("high importance note", importance=9, db_path=db)
    with memory._connect(db) as conn:
        for mid in (low_id, high_id):
            conn.execute("UPDATE memories SET created = ?, last_used = ? "
                         "WHERE id = ?", (NOW - 30 * DAY, NOW - 30 * DAY, mid))
    hits = retrieval.scored_search("importance note", db_path=db, now=NOW)
    check("higher importance outranks lower when otherwise equal",
          len(hits) >= 2 and hits[0]["id"] == high_id and hits[1]["id"] == low_id)

    # Archived and superseded rows never appear, even if relevant.
    arch_id = memory.add_memory("archived dog biscuit", db_path=db)
    sup_id = memory.add_memory("superseded dog biscuit", db_path=db)
    with memory._connect(db) as conn:
        conn.execute("UPDATE memories SET archived = 1 WHERE id = ?", (arch_id,))
        conn.execute("UPDATE memories SET superseded_by = ? WHERE id = ?",
                     (arch_id + 1, sup_id))
    hits = retrieval.scored_search("biscuit", db_path=db, now=NOW)
    check("archived and superseded memories never appear",
          all(h["id"] not in (arch_id, sup_id) for h in hits))

    print("bump_use")
    before = None
    with memory._connect(db) as conn:
        row = conn.execute("SELECT use_count, last_used FROM memories WHERE id = ?",
                           (recent_id,)).fetchone()
        before = (row["use_count"], row["last_used"])
    n = retrieval.bump_use([recent_id, old_id, 999_999_999], db_path=db)
    check("unknown ids ignored", n == 2)
    with memory._connect(db) as conn:
        row = conn.execute("SELECT use_count, last_used FROM memories WHERE id = ?",
                           (recent_id,)).fetchone()
    check("use_count incremented and last_used set",
          row["use_count"] == before[0] + 1
          and row["last_used"] is not None and row["last_used"] >= before[1])

    print("edge cases")
    check("empty query returns []", retrieval.scored_search("", db_path=db) == [])
    check("no-match query returns []",
          retrieval.scored_search("zzzzzqqqqq", db_path=db) == [])
    # Injecting `now` makes scores deterministic: recency is computed from
    # last_used/created relative to the injected clock, not the wall clock.
    with memory._connect(db) as conn:
        conn.execute("UPDATE memories SET created = ?, last_used = ? "
                     "WHERE id = ?", (NOW - 60 * DAY, NOW - 60 * DAY, recent_id))
    h_now = retrieval.scored_search("runs local LLM nightly", db_path=db, now=NOW)
    h_later = retrieval.scored_search("runs local LLM nightly", db_path=db,
                                       now=NOW + 5 * DAY)
    check("`now` can be injected for deterministic tests",
          h_now[0]["final_score"] > 0
          and h_now[0]["final_score"] >= h_later[0]["final_score"]
          and h_now[0]["id"] == h_later[0]["id"])
    check("limit respected",
          len(retrieval.scored_search("memory", db_path=db, limit=2, now=NOW)) <= 2)

print(f"\nAll {passed} checks passed.")
