"""
JARVIS bridge: a small local MCP server so Claude Desktop can inspect, test and (with fences) edit
the JARVIS folder. Lives OUTSIDE the JARVIS folder, so none of its own tools can edit it.

Fences:
- Every path is resolved, then must be inside JARVIS_ROOT (blocks .., symlinks, JARVIS_evil siblings).
- Never readable/writable: .git internals, *.env, *.key, *.pem, Windows stream names (file:stream).
- Writes, commits and reverts only work while the git branch is `self-improve`.
- Protected files (policy, guards in tools/, eval/, config/, rules, .gitignore) cannot be written
  unless the HUMAN creates a file named UNLOCK_PROTECTED.txt in the JARVIS folder. Delete it to re-lock.
- No tool runs arbitrary commands. Git and the eval use fixed argument lists, never a shell.
- Claude Desktop also asks you to approve tool calls.
"""
import functools, os, subprocess
from pathlib import Path

ROOT = Path(os.environ.get("JARVIS_ROOT", r"D:\AI models\JARVIS")).resolve()
PY = os.environ.get("JARVIS_PYTHON", "python")
BRANCH = "self-improve"
MAX_WRITE = 200_000
MAX_OUT = 20_000
PROTECTED_FILES = {"policy.json", "claude.md", "start_prompt.md", ".gitignore", "unlock_protected.txt"}
PROTECTED_DIRS = (".claude/", "eval/", "tools/", "config/")
UNLOCK = ROOT / "UNLOCK_PROTECTED.txt"


class Refused(Exception):
    pass


def _rel(p):
    return "." if p == ROOT else p.relative_to(ROOT).as_posix()


def safe_path(path):
    p = (ROOT / path).resolve()
    if not p.is_relative_to(ROOT):
        raise Refused("path is outside the JARVIS folder")
    parts = p.relative_to(ROOT).parts
    if ".git" in [x.lower() for x in parts]:
        raise Refused(".git internals are off limits")
    if any(":" in x or x.endswith((".", " ")) for x in parts):
        raise Refused("suspicious path name")
    n = p.name.lower()
    if n == ".env" or n.endswith((".env", ".key", ".pem")):
        raise Refused("secret files are off limits")
    return p


def is_protected(p):
    rel = _rel(p).lower()
    return rel in PROTECTED_FILES or rel.startswith(PROTECTED_DIRS)


def _check_writable(p):
    if p.name.lower() == "unlock_protected.txt":
        raise Refused("only the human can create or change the unlock file")
    if is_protected(p) and not UNLOCK.exists():
        raise Refused(f"'{_rel(p)}' is protected. To allow it, the human must create UNLOCK_PROTECTED.txt "
                      f"in the JARVIS folder (delete it afterwards to re-lock).")


def _git(*args, timeout=30):
    r = subprocess.run(["git", "-C", str(ROOT), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout,
                       encoding="utf-8", errors="replace", env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
    return (r.stdout + r.stderr).rstrip(), r.returncode


def _need_branch():
    b, _ = _git("rev-parse", "--abbrev-ref", "HEAD")
    if b != BRANCH:
        raise Refused(f"on branch '{b}', not '{BRANCH}'. Writes are only allowed on {BRANCH}.")


def _cut(s, n=MAX_OUT):
    return s if len(s) <= n else s[:n] + f"\n...[truncated, {len(s) - n} more chars]"


def _tool(f):
    @functools.wraps(f)
    def w(*a, **k):
        try:
            return f(*a, **k)
        except Refused as e:
            return f"REFUSED: {e}"
        except subprocess.TimeoutExpired:
            return "ERROR: timed out"
        except Exception as e:
            return f"ERROR: {type(e).__name__}: {e}"
    return w


@_tool
def jarvis_status():
    """Current git branch, uncommitted changes, and whether protected files are unlocked."""
    b, _ = _git("rev-parse", "--abbrev-ref", "HEAD")
    s, _ = _git("status", "--short")
    return f"branch: {b}\nprotected files unlocked: {UNLOCK.exists()}\nchanges:\n{s or '(clean)'}"


@_tool
def jarvis_list(path: str = "."):
    """List files and folders inside the JARVIS folder (one level)."""
    p = safe_path(path)
    if not p.is_dir():
        raise Refused("not a folder")
    rows = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
    return "\n".join(f"{'[dir] ' if x.is_dir() else '      '}{x.name}" for x in rows if x.name != ".git")


@_tool
def jarvis_read(path: str, start_line: int = 1, end_line: int = 400):
    """Read a text file (line-numbered). Use start_line/end_line to read only what you need."""
    p = safe_path(path)
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    s, e = max(1, start_line), min(len(lines), end_line)
    body = "\n".join(f"{i}: {lines[i - 1]}" for i in range(s, e + 1))
    return _cut(f"{_rel(p)} (lines {s}-{e} of {len(lines)})\n{body}")


@_tool
def jarvis_write(path: str, content: str):
    """Create or overwrite a file. Only on branch self-improve; protected files refused unless unlocked."""
    p = safe_path(path)
    _check_writable(p)
    _need_branch()
    if len(content) > MAX_WRITE:
        raise Refused("content too large")
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(content)
    return f"wrote {_rel(p)} ({len(content)} chars)"


@_tool
def jarvis_edit(path: str, old: str, new: str):
    """Replace one exact piece of text in a file. 'old' must appear exactly once. Cheaper than rewriting."""
    p = safe_path(path)
    _check_writable(p)
    _need_branch()
    text = p.read_text(encoding="utf-8")
    n = text.count(old)
    if n != 1:
        raise Refused(f"'old' text found {n} times; it must appear exactly once")
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(text.replace(old, new, 1))
    return f"edited {_rel(p)}"


@_tool
def jarvis_run_eval():
    """Run the dry-run routing test (python eval/run_eval.py) and return its output."""
    r = subprocess.run([PY, "eval/run_eval.py"], cwd=ROOT, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=180,
                       encoding="utf-8", errors="replace")
    return _cut(f"exit code {r.returncode}\n{r.stdout}\n{r.stderr}".strip(), 8000)


@_tool
def jarvis_diff(path: str = ""):
    """Show uncommitted changes (git diff against the last commit), optionally for one file."""
    args = ["diff", "HEAD"]
    if path:
        args += ["--", _rel(safe_path(path))]
    out, _ = _git(*args)
    return _cut(out or "(no changes)")


@_tool
def jarvis_log(n: int = 10):
    """Show the last n commits."""
    out, _ = _git("log", "--oneline", f"-{max(1, min(n, 50))}")
    return out


@_tool
def jarvis_commit(message: str):
    """Commit all changes on self-improve. Refused if protected files changed without the unlock file."""
    _need_branch()
    st, _ = _git("status", "--porcelain")
    if not st:
        raise Refused("nothing to commit")
    if not UNLOCK.exists():
        bad = []
        for line in st.splitlines():
            name = line[3:].split(" -> ")[-1].strip().strip('"')
            if is_protected(ROOT / name):
                bad.append(name)
        if bad:
            raise Refused("protected files changed (" + ", ".join(bad) + "). The human must review and "
                          "commit these, or create UNLOCK_PROTECTED.txt.")
    _git("add", "-A")
    out, code = _git("commit", "-m", message[:200])
    return out if code == 0 else f"ERROR: {out}"


@_tool
def jarvis_revert_last_commit():
    """Undo the last commit safely by adding a new 'revert' commit (history is kept). Only on self-improve."""
    _need_branch()
    out, _ = _git("revert", "--no-edit", "HEAD")
    return out


@_tool
def jarvis_discard_file(path: str):
    """Throw away uncommitted changes to one file (restore it to the last commit). Only on self-improve."""
    p = safe_path(path)
    _check_writable(p)
    _need_branch()
    out, code = _git("checkout", "--", _rel(p))
    return "restored " + _rel(p) if code == 0 else f"ERROR: {out}"


TOOLS = [jarvis_status, jarvis_list, jarvis_read, jarvis_write, jarvis_edit, jarvis_run_eval,
         jarvis_diff, jarvis_log, jarvis_commit, jarvis_revert_last_commit, jarvis_discard_file]


def main():
    from mcp.server.fastmcp import FastMCP
    mcp = FastMCP("jarvis-bridge")
    for f in TOOLS:
        mcp.tool()(f)
    mcp.run()


if __name__ == "__main__":
    main()
