"""test_extraction.py - Phase 2 checks. Run: python test_extraction.py

Uses a temporary database, so it never touches the real memory.db.
"""

import sys
import tempfile
from pathlib import Path

import memory
import extraction

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
    memory.init_db(db_path=db)

    print("parse_candidates")
    check("fenced JSON parses",
          extraction.parse_candidates('```json\n[{"text": "a", "type": "fact", "importance": 5}]\n```')
          == [{"text": "a", "type": "fact", "importance": 5}])
    check("plain JSON parses",
          extraction.parse_candidates('[{"text": "a", "type": "fact", "importance": 5}]')
          == [{"text": "a", "type": "fact", "importance": 5}])
    check("garbage returns []", extraction.parse_candidates("hello world") == [])
    check("empty string returns []", extraction.parse_candidates("") == [])
    check("non-string returns []", extraction.parse_candidates(None) == [])
    check("over-long text dropped",
          extraction.parse_candidates(
              '[{"text": "x" * 201 + "x", "type": "fact", "importance": 5}]') == [])
    check("invalid type dropped",
          extraction.parse_candidates(
              '[{"text": "a", "type": "bogus", "importance": 5}]') == [])
    check("importance clamped to 1",
          extraction.parse_candidates(
              '[{"text": "a", "type": "fact", "importance": 0}]')
          == [{"text": "a", "type": "fact", "importance": 1}])
    check("importance clamped to 10",
          extraction.parse_candidates(
              '[{"text": "a", "type": "fact", "importance": 99}]')
          == [{"text": "a", "type": "fact", "importance": 10}])
    check("max 3 kept",
          len(extraction.parse_candidates(
              '[{"text": "a", "type": "fact", "importance": 5},'
              ' {"text": "b", "type": "fact", "importance": 5},'
              ' {"text": "c", "type": "fact", "importance": 5},'
              ' {"text": "d", "type": "fact", "importance": 5}]')) == 3)
    check("non-dict items dropped",
          extraction.parse_candidates('[1, "a", {"text": "x", "type": "fact", "importance": 3}]')
          == [{"text": "x", "type": "fact", "importance": 3}])

    # Fix pass: numeric importance coercion
    check("importance as numeric string accepted",
          extraction.parse_candidates(
              '[{"text": "a", "type": "fact", "importance": "8"}]')
          == [{"text": "a", "type": "fact", "importance": 8}])
    check("importance as float accepted",
          extraction.parse_candidates(
              '[{"text": "a", "type": "fact", "importance": 7.0}]')
          == [{"text": "a", "type": "fact", "importance": 7}])
    check("importance as non-numeric string rejected",
          extraction.parse_candidates(
              '[{"text": "a", "type": "fact", "importance": "abc"}]') == [])
    check("importance as bool rejected",
          extraction.parse_candidates(
              '[{"text": "a", "type": "fact", "importance": true}]') == [])
    # Fix pass: lowercase type
    check("type lowercased before validation",
          extraction.parse_candidates(
              '[{"text": "a", "type": "FACT", "importance": 5}]')
          == [{"text": "a", "type": "fact", "importance": 5}])

    print("process_candidate")
    # First insert.
    r1 = extraction.process_candidate(
        {"text": "User runs RTX 3090", "type": "fact", "importance": 7}, db_path=db)
    check("first candidate inserts", r1["action"] == "inserted" and r1["id"] > 0)
    # Duplicate: same text, jaccard = 1.0 >= 0.8.
    r2 = extraction.process_candidate(
        {"text": "User runs RTX 3090", "type": "fact", "importance": 7}, db_path=db)
    check("duplicate detected", r2["action"] == "duplicate" and r2["id"] == r1["id"])
    # Confidence bumped by 0.1.
    with memory._connect(db) as conn:
        row = conn.execute("SELECT confidence, use_count FROM memories WHERE id = ?",
                            (r1["id"],)).fetchone()
    check("confidence bumped", abs(row["confidence"] - 0.6) < 1e-9)
    check("use_count incremented", row["use_count"] == 1)

    print("process_candidate punctuation")
    r4 = extraction.process_candidate(
        {"text": "User prefers terse answers", "type": "preference", "importance": 6}, db_path=db)
    check("punctuation: new fact inserts",
          r4["action"] == "inserted")
    r5 = extraction.process_candidate(
        {"text": "User prefers terse answers.", "type": "preference", "importance": 6}, db_path=db)
    check("punctuation: duplicate detected",
          r5["action"] == "duplicate" and r5["id"] == r4["id"])

    print("supersede")
    old_id = r1["id"]
    r3 = extraction.process_candidate(
        {"text": "Completely different text", "type": "fact", "importance": 5}, db_path=db)
    extraction.supersede(old_id, r3["id"], db_path=db)
    hits = memory.search_keyword("User runs RTX", db_path=db)
    check("supersede hides old from search_keyword",
          all(h["id"] != old_id for h in hits))
    # ValueError on non-existent id.
    try:
        extraction.supersede(old_id, 999999, db_path=db)
        check("supersede ValueError on missing id", False)
    except ValueError:
        check("supersede ValueError on missing id", True)
    # ValueError when old_id == new_id.
    try:
        extraction.supersede(old_id, old_id, db_path=db)
        check("supersede ValueError on old_id == new_id", False)
    except ValueError:
        check("supersede ValueError on old_id == new_id", True)

    print("extract_and_store")
    # Failing llm_fn returns [].
    def bad_llm(prompt):
        raise RuntimeError("boom")
    check("failing llm_fn returns []",
          extraction.extract_and_store("hi", "hello", bad_llm, db_path=db) == [])
    # End-to-end with fake llm_fn.
    def fake_llm(prompt):
        return '[{"text": "User prefers dark mode", "type": "preference", "importance": 8}]'
    results = extraction.extract_and_store(
        "I like dark mode", "Got it, dark mode noted.", fake_llm, db_path=db)
    check("end-to-end inserts expected row",
          len(results) == 1 and results[0]["action"] == "inserted")
    with memory._connect(db) as conn:
        row = conn.execute("SELECT * FROM memories WHERE id = ?",
                            (results[0]["id"],)).fetchone()
    check("row has correct type and importance",
          row["type"] == "preference" and row["importance"] == 8)
    check("row has confidence 0.5", abs(row["confidence"] - 0.5) < 1e-9)

    # Fix pass: 100000 nested brackets
    check("100000 nested brackets returns []",
          extraction.parse_candidates("[" * 100000) == [])

    # Fix pass: process_candidate failure is swallowed
    def failing_llm(prompt):
        return '[{"text": "some text", "type": "fact", "importance": 5}]'
    try:
        extraction.extract_and_store(
            "hi", "hello", failing_llm, source_episode=99999, db_path=db)
        check("nonexistent source_episode returns without raising", True)
    except Exception:
        check("nonexistent source_episode returns without raising", False)

print(f"\nAll {passed} checks passed.")
