"""Safety tests for the bridge. Runs in a temporary git repo; touches nothing real."""
import os, subprocess, sys, tempfile, pathlib

tmp = pathlib.Path(tempfile.mkdtemp()).resolve()
root = tmp / "JARVIS"
(root / "tools").mkdir(parents=True)
(root / "eval").mkdir()
(tmp / "JARVIS_evil").mkdir()
(tmp / "JARVIS_evil" / "x.txt").write_text("evil")
(root / "agent.py").write_text("print('hi')\n")
(root / "tools" / "shell.py").write_text("# guard\n")
(root / "jarvis.env").write_text("KEY=secret\n")
(root / "eval" / "run_eval.py").write_text("print('SCORE 1/1')\n")
os.environ["JARVIS_ROOT"] = str(root)
os.environ["JARVIS_PYTHON"] = sys.executable
g = lambda *a: subprocess.run(["git", "-C", str(root), *a], capture_output=True, text=True)
g("init"); g("config", "user.email", "t@t"); g("config", "user.name", "t")
g("checkout", "-b", "self-improve"); g("add", "agent.py", "tools", "eval"); g("commit", "-m", "base")
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import jarvis_bridge as b

fails = []
def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond: fails.append(name)

check("read inside root works", "print('hi')" in b.jarvis_read("agent.py"))
check("'..' escape refused", b.jarvis_read("../JARVIS_evil/x.txt").startswith("REFUSED"))
if os.name == "nt":
    check("'..' escape refused (backslashes)", b.jarvis_read("..\\JARVIS_evil\\x.txt").startswith("REFUSED"))
check("absolute path elsewhere refused", b.jarvis_read(str(tmp / "JARVIS_evil" / "x.txt")).startswith("REFUSED"))
check("env file refused", b.jarvis_read("jarvis.env").startswith("REFUSED"))
check(".git refused", b.jarvis_read(".git/config").startswith("REFUSED"))
check("stream name refused", b.jarvis_read("agent.py:hidden").startswith("REFUSED"))
check("write ok on self-improve", b.jarvis_write("notes.txt", "hi").startswith("wrote"))
check("edit unique ok", b.jarvis_edit("agent.py", "hi", "hello").startswith("edited"))
check("edit non-unique refused", b.jarvis_edit("notes.txt", "x", "y").startswith("REFUSED"))
check("protected write refused", b.jarvis_write("tools/shell.py", "# evil").startswith("REFUSED"))
check("protected eval write refused", b.jarvis_write("eval/run_eval.py", "x").startswith("REFUSED"))
check("cannot write unlock file", b.jarvis_write("UNLOCK_PROTECTED.txt", "x").startswith("REFUSED"))
check("run eval works", "SCORE 1/1" in b.jarvis_run_eval())
out = b.jarvis_commit("test")
check("commit ok (no protected changes)", not out.startswith(("REFUSED", "ERROR")))
(root / "tools" / "shell.py").write_text("# human edit\n")
check("commit refused when protected changed", b.jarvis_commit("sneaky").startswith("REFUSED"))
(root / "UNLOCK_PROTECTED.txt").write_text("")
check("protected write allowed after human unlock", b.jarvis_write("tools/shell.py", "# ok").startswith("wrote"))
(root / "UNLOCK_PROTECTED.txt").unlink()
g("checkout", "-q", "-b", "main")
check("write refused off branch", b.jarvis_write("a.txt", "x").startswith("REFUSED"))
check("commit refused off branch", b.jarvis_commit("x").startswith("REFUSED"))
print("\nALL PASSED" if not fails else f"\nFAILED: {fails}")
sys.exit(1 if fails else 0)
