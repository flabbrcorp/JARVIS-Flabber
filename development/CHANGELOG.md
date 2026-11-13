# Shared changelog

## 2026-11-12

- **Codex — Local Desktop recovery point.** Source commit `af3888c6e02e605728e8ea4395c59ca4d3e73f31` captured the reviewed Desktop files and stopped tracking five legacy runtime records. On-disk files were preserved. See the [baseline record](agents/CODEX.md#2026-11-12--desktop-recovery-point).
- **Codex — Desktop Git baseline review.** Reviewed the candidate paths and stopped before staging after finding hardcoded user identity in required Desktop files and legacy memory paths already tracked by the parent commit. The source index was empty and HEAD remained `df57449`. See the [review entry](agents/CODEX.md#2026-11-12--desktop-git-baseline-review).
- **Codex — Shared journal setup.** Created the journal documents and Git ignore policy, inspected Desktop and legacy documentation, and added the source-side Codex and Cline entry points. See the [setup entry](agents/CODEX.md#2026-11-12--shared-journal-setup). Earlier Desktop test evidence is linked from [Current State](CURRENT_STATE.md).
- **Cline — Onboarding verification.** Read all development instruction files (`CLAUDE.md`, `START_PROMPT.md`, `AGENTS.md`, `.claude/settings.json`, `memory.md`, `development/README.md`, `CURRENT_STATE.md`, `DECISIONS.md`, `OPEN_ISSUES.md`, `CHANGELOG.md`, `CODEX.md`, Memory Bank files). Verified Git tracking status: `desktop/` untracked in source repo, journal repo clean. Documented discrepancies (stale `techContext.md` paths, legacy vs. Desktop memory path mismatch). See [Cline's journal](agents/CLINE.md#2026-11-12--onboarding-verification).

## 2026-11-13

- Codex added reversible chat hiding and tested its recall filter. See the [test record](agents/CODEX.md#2026-11-13--reversible-chat-hiding).

- Codex added model-aware settings and a Windows launcher. See the [test record](agents/CODEX.md#2026-11-13--settings-and-windows-launcher).

- Codex repaired the installed Jarvis Start menu shortcut identity and verified its launcher target.
