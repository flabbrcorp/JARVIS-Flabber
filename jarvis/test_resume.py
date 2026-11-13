"""Tests for jarvis_resume.py. Uses a temporary folder only; never touches the real memory.db.

Run from the JARVIS folder:  python -m unittest test_resume -v
"""
import pathlib
import sqlite3
import tempfile
import unittest

import jarvis_memory as mem
import jarvis_resume as res

MD = """# Memory
## The User
- Name: flab
## Active Projects
- Building the memory brief
## Standing Rules
- Confirm before deleting
## Notes / Log
- 2026-10-28: first note
- 2026-10-29: second note
"""


class ResumeBriefTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = pathlib.Path(self.tmp.name)
        self.md = d / "memory.md"
        self.md.write_text(MD, encoding="utf-8")
        self.db = str(d / "scratch.db")
        mem.log_episode("old", "user", "resume the memory project", db_path=self.db)
        mem.log_episode("old", "assistant", "ok, building the brief", db_path=self.db)
        mem.log_episode("now", "user", "hello there", db_path=self.db)
        mem.add_memory("flab likes simple explanations", importance=9, db_path=self.db)
        mem.add_memory("archived secret fact", importance=10, db_path=self.db)
        conn = sqlite3.connect(self.db)
        conn.execute("UPDATE memories SET archived = 1 WHERE text = 'archived secret fact'")
        conn.commit()
        conn.close()

    def tearDown(self):
        self.tmp.cleanup()

    def brief(self, **kw):
        return res.build_resume_brief(memory_md=self.md, db_path=self.db, **kw)

    def test_includes_last_chat_and_excludes_current_session(self):
        b = self.brief(current_session="now")
        self.assertIn("resume the memory project", b)
        self.assertNotIn("hello there", b)

    def test_includes_project_notes_and_user(self):
        b = self.brief(current_session="now")
        self.assertIn("Building the memory brief", b)
        self.assertIn("second note", b)
        self.assertIn("Name: flab", b)

    def test_includes_active_memory_but_not_archived(self):
        b = self.brief(current_session="now")
        self.assertIn("flab likes simple explanations", b)
        self.assertNotIn("archived secret fact", b)

    def test_respects_max_chars(self):
        b = self.brief(current_session="now", max_chars=200)
        self.assertLessEqual(len(b), 200)

    def test_missing_files_give_empty_string(self):
        b = res.build_resume_brief(memory_md=pathlib.Path(self.tmp.name) / "nope.md",
                                   db_path=pathlib.Path(self.tmp.name) / "nope.db")
        self.assertEqual(b, "")

    def test_does_not_modify_database(self):
        before = pathlib.Path(self.db).read_bytes()
        self.brief(current_session="now")
        self.assertEqual(before, pathlib.Path(self.db).read_bytes())


if __name__ == "__main__":
    unittest.main()
