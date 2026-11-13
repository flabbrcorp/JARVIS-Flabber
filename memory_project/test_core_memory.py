"""test_core_memory.py - Phase 2 checks. Run: python test_core_memory.py

Uses a temporary database, so it never touches the real memory.db.
"""

import sys
import tempfile
from pathlib import Path

import core_memory
from core_memory import CoreMemoryFull, MAX_CHARS

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

    print("set / get / replace / delete")
    core_memory.set_core("name", "Sam", db_path=db)
    core_memory.set_core("tone", "casual", db_path=db)
    core_memory.set_core("project", "local LLM", db_path=db)
    block = core_memory.get_core_block(db_path=db)
    check("set stores entries", block == "name: Sam\nproject: local LLM\ntone: casual\n")
    core_memory.set_core("tone", "terse", db_path=db)
    block = core_memory.get_core_block(db_path=db)
    check("replace updates value in place", block == "name: Sam\nproject: local LLM\ntone: terse\n")
    check("delete returns True and removes", core_memory.delete_core("project", db_path=db))
    block = core_memory.get_core_block(db_path=db)
    check("deleted entry is gone", "project" not in block)
    check("delete of unknown key returns False", not core_memory.delete_core("nope", db_path=db))

    print("size cap")
    # Reset: wipe all entries.
    core_memory.delete_core("name", db_path=db)
    core_memory.delete_core("tone", db_path=db)
    core_memory.delete_core("project", db_path=db)
    filler = "x" * 2985
    core_memory.set_core("filler", filler, db_path=db)
    core_memory.set_core("name", "Sam", db_path=db)
    # name:Sam = 8 chars. 2985 + 8 = 2993 < 3000.
    # Now try to add another key that would push over.
    try:
        core_memory.set_core("extra", "y" * 12, db_path=db)
        check("size cap raises CoreMemoryFull", False)
    except CoreMemoryFull:
        check("size cap raises CoreMemoryFull", True)
    # Data must be unchanged.
    block = core_memory.get_core_block(db_path=db)
    check("data unchanged after CoreMemoryFull", block.count("filler: ") == 1
          and "extra" not in block)
    # Replacing an existing value that stays under cap succeeds even when
    # the store is nearly full. filler:xx = 7 chars (key 7 + value 12... wait).
    # Current: filler:xx = 2997 chars. name:Sam = 7. Total = 3004? No:
    # filler key len=7, value=2990, total=2997. name key=5, value=3, total=8.
    # Sum = 3005? But we set name before filler, so name is already there.
    # Let's just verify: replacing filler with a shorter value.
    try:
        core_memory.set_core("filler", "y" * 2900, db_path=db)
        check("replace under cap succeeds", True)
    except CoreMemoryFull:
        check("replace under cap succeeds", False)
    block = core_memory.get_core_block(db_path=db)
    check("replaced value is updated", "filler: " + "y" * 2900 in block)

    print("empty block")
    # Wipe everything.
    core_memory.delete_core("filler", db_path=db)
    core_memory.delete_core("name", db_path=db)
    block = core_memory.get_core_block(db_path=db)
    check("empty store returns empty string", block == "")

    print("whitespace validation")
    try:
        core_memory.set_core("  ", "val", db_path=db)
        check("whitespace-only key rejected", False)
    except ValueError:
        check("whitespace-only key rejected", True)
    try:
        core_memory.set_core("key", "   ", db_path=db)
        check("whitespace-only value rejected", False)
    except ValueError:
        check("whitespace-only value rejected", True)

print(f"\nAll {passed} checks passed.")
