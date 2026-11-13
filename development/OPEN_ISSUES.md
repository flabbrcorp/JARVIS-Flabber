# Open issues

## JARVIS-001 — Desktop baseline outside source Git history

- **Status / owner:** VERIFIED-RESOLVED / Codex.
- **Component / severity:** Source control, medium. The current Desktop behavior depends on local files absent from the current source commit.
- **Evidence and reproduction:** `git -C D:\AI_JARVIS\jarvis status --short` on 2026-11-12 showed `desktop/`, the Desktop launcher, and Desktop config as untracked. HEAD was `df57449`. The working tree also had unrelated changes.
- **Resolution:** Local source commit `af3888c6e02e605728e8ea4395c59ca4d3e73f31` contains the reviewed Desktop files and required configuration. Verified the commit and preserved unrelated working changes. See the [baseline record](agents/CODEX.md#2026-11-12--desktop-recovery-point).

## JARVIS-002 — Near-full context behavior is unknown

- **Status / owner:** SUSPECTED / unassigned. No failure was observed during the short probes.
- **Component / severity:** Desktop inference, low for current short chats. Latency and memory pressure under near-full 64K or 128K inputs are unmeasured.
- **Evidence and reproduction:** The 2026-11-12 sweep sent short prompts and checked `/api/ps` and `ollama ps`. Its results cover load and generation, with no near-full input run. See [prior Desktop evidence](agents/CODEX.md#prior-desktop-evidence-2026-11-12).
- **Related work:** A longer-input test is a separate investigation if Flab requests it.
