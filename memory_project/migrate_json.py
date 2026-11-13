"""migrate_json.py - import legacy JSON memory files into memory.db.

Usage:
    python migrate_json.py notes1.json notes2.json [--db memory.db] [--dry-run]

Safety:
  - Each JSON file is copied to <name>.bak-<timestamp> before anything else.
  - The original JSON files are never modified or deleted.
  - Re-running is safe: entries already imported as type='legacy' are skipped.

Because the exact shape of your JSON files isn't known, the flattening is
deliberately permissive. It handles:
  - a list of strings                      ["likes tea", ...]
  - a list of dicts with a text-like key   [{"text": "..."}, {"fact": "..."}]
  - a dict of key -> value                 {"name": "Sam"} -> "name: Sam"
  - nested combinations of the above       (key paths are joined with " > ")
Adjust flatten() if your files look different.
"""

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

import memory

TEXT_KEYS = ("text", "content", "memory", "fact", "note", "value", "summary")


def flatten(obj, prefix=""):
    """Yield one plain-text string per leaf entry in a JSON structure."""
    if isinstance(obj, str):
        text = obj.strip()
        if text:
            yield f"{prefix}: {text}" if prefix else text
    elif isinstance(obj, (int, float, bool)):
        yield f"{prefix}: {obj}" if prefix else str(obj)
    elif isinstance(obj, list):
        for item in obj:
            yield from flatten(item, prefix)
    elif isinstance(obj, dict):
        # A dict with a recognizable text field is one entry, not a subtree.
        for k in TEXT_KEYS:
            if isinstance(obj.get(k), str) and obj[k].strip():
                yield (f"{prefix}: " if prefix else "") + obj[k].strip()
                return
        for k, v in obj.items():
            new_prefix = f"{prefix} > {k}" if prefix else str(k)
            yield from flatten(v, new_prefix)


def backup(path):
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dest = path.with_name(f"{path.name}.bak-{stamp}")
    shutil.copy2(path, dest)
    return dest


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", help="legacy JSON memory files")
    ap.add_argument("--db", default=memory.DEFAULT_DB)
    ap.add_argument("--dry-run", action="store_true",
                    help="show what would be imported, write nothing")
    args = ap.parse_args()

    paths = [Path(f) for f in args.files]
    for p in paths:
        if not p.is_file():
            sys.exit(f"File not found: {p}")

    entries = []
    for p in paths:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            sys.exit(f"{p} is not valid JSON: {e}")
        found = list(flatten(data))
        print(f"{p}: {len(found)} entries found")
        entries.extend(found)

    if args.dry_run:
        for e in entries:
            print("  would import:", e)
        return

    for p in paths:
        print(f"backed up {p} -> {backup(p)}")

    memory.init_db(args.db)
    with memory._connect(args.db) as conn:
        existing = {r["text"] for r in
                    conn.execute("SELECT text FROM memories WHERE type='legacy'")}

    imported = skipped = 0
    for text in entries:
        if text in existing:
            skipped += 1
            continue
        memory.add_memory(text, type="legacy", importance=5,
                          confidence=0.5, db_path=args.db)
        existing.add(text)
        imported += 1

    print(f"done: {imported} imported, {skipped} skipped as duplicates")


if __name__ == "__main__":
    main()
