# Codex work journal

## 2026-11-12 — Desktop recovery point

- Flab authorized the existing aliases in Desktop source and index-only removal of legacy runtime records. Created local source commit `af3888c6e02e605728e8ea4395c59ca4d3e73f31` with message `Baseline Jarvis Desktop before reliability tests`.
- **VERIFIED.** `git diff --cached --name-status` matched the reviewed allowlist, including Desktop source, launcher, config, eval, both instruction files, and the updated ignore rules. Staged credential pattern scan found no matches. The whitespace check passed with pre-existing blank lines at EOF exempted. No application source edits were made.
- **VERIFIED.** `git rm --cached` stopped tracking the legacy memory note, conversation history, feedback and tool-call logs, and current-task state. SHA-256 checks before staging and after commit confirmed their bytes remained intact. `git ls-tree` confirmed they were absent from the new tree. Earlier commits retain their historical copies.
- **VERIFIED.** `git remote` listed no remotes in either repository. Source HEAD advanced by one commit with the original parent. The source index is empty and unrelated local changes remain. No inference tests ran in this session.

## 2026-11-12 — Desktop Git baseline review

- **VERIFIED.** `git status --short --untracked-files=all`, `git ls-files`, `git ls-tree -r --name-only HEAD -- memory.md memory state`, and `git diff --cached --name-only` identified the source candidates, pre-existing tracked legacy memory and logs, and an empty index. HEAD was `df57449bf7020d19c20405a8b1ef94e33e19a688`.
- The candidate paths were `desktop/*.py`, `desktop/README.md`, `desktop/requirements.txt`, `Jarvis Desktop.pyw`, `eval/desktop_baseline.py`, `config/desktop.json`, `AGENTS.md`, and `.clinerules/shared-development.md`. A common credential pattern scan found no matches. Direct inspection found the primary user's aliases in `desktop/identity.py`, `desktop/chat.py`, and `desktop/README.md`. The chat module imports the identity module, so omitting them would produce an incomplete recovery point.
- **TESTED-PASS.** Desktop Python 3.13 parsed all nine Python source candidates using `ast.parse` without importing them or starting Desktop. A first credential scan invocation had an argument error and was rerun successfully.
- Stopped before staging under the personal-data constraint. No application source was changed and no commit was made. [JARVIS-001](../OPEN_ISSUES.md#jarvis-001--desktop-baseline-outside-source-git-history) remains confirmed. Resolve the inclusion of the hardcoded aliases and clarify whether the recovery point may inherit the existing legacy memory paths before committing.

## 2026-11-12 — Shared journal setup

- Created the seven journal documents and `development/.gitignore`. Added `jarvis/AGENTS.md` and `jarvis/.clinerules/shared-development.md` as entry points. Preserved the existing Cline Memory Bank and source working changes.
- **VERIFIED.** In PowerShell on Windows, `git -C D:\AI_JARVIS\jarvis status --short` and `git rev-parse --show-toplevel` established the Git boundary and existing local changes. Git reported that the project root was outside a repository. The journal uses its own Git boundary for that reason.
- **VERIFIED.** `Get-Process pythonw`, the launcher process command line, `config/desktop.json`, and `ollama list` with `OLLAMA_HOST=127.0.0.1:11435` established the Desktop baseline recorded in Current State. This session did not rerun the earlier inference probes.
- Found a scope mismatch in the legacy Memory Bank and the Desktop documentation. The Memory Bank describes `memory.py`, `memory.db`, and `memory.md`. The Desktop path uses `desktop/chat.py` and `data/desktop.sqlite3`. [Open issues](../OPEN_ISSUES.md) records the source tracking gap and the untested high-context workload.
- **VERIFIED.** `git -C development diff --cached --check` passed. `git -C development check-ignore` matched sample SQLite, environment, model, and generated result paths. The source-side pointers remain untracked. Existing application Git history already includes legacy JSONL logs, so review source staging by path.

## Prior Desktop evidence (2026-11-12)

These references identify earlier executed work. Evidence files are stored outside the journal repository.

- **TESTED-PASS.** Windows Desktop Python 3.13 with offscreen PySide6 ran `python -B work/test_desktop_reset.py` against a restored and reset scratch database. The exact name save succeeded without calling Ollama, and the standing note appeared in a fresh prompt after reopening SQLite. The test also exercised save rejection and transcript filtering.
- **TESTED-PASS.** `python -B work/context_sweep.py` used the Desktop Ollama adapter on loopback, an in-memory chat database, and the local RTX 4070. The six requested sizes matched Ollama's reported effective sizes and generated short replies. Both model switches at 16K completed. See `outputs/ollama-context-verification.txt` in the Codex workspace `C:\Users\flab\Documents\Codex\2026-11-12\jarvis-desktop-conversational-memory-capability-audit`.
- **TESTED-PASS.** `python -B work/context_ui_check.py` and the separate `restart` invocation used offscreen Desktop and mocked Ollama responses. The UI reverted to 16K after a simulated 64K HTTP error and a simulated 128K effective-size mismatch. A separate process restored the saved value from an isolated settings file.

## 2026-11-13 — Reversible chat hiding

- Updated desktop/chat.py and desktop/window.py. Sidebar actions rename, hide, and restore. SQLite v5 defaults existing chats to visible and filters hidden transcripts from ordinary recall.
- TESTED-PASS. Ran work/jarvis-chat-visibility/test_visibility.py with Desktop Python 3.13, QT_QPA_PLATFORM=offscreen, and the live source checkout on PYTHONPATH. A disposable SQLite database verified v4 migration, GUI hide and restore, hiding the last visible chat, reopen persistence, recall exclusion and restoration, and retention of transcripts, memories, and revisions.
- Live database migration and the Ollama evaluation suite were outside this run. Natural-language log deletion remains a separate tool milestone with permission and confirmation.

## 2026-11-13 — Settings and Windows launcher

- Added model-aware settings in desktop/backend.py and desktop/window.py. Thinking follows Ollama's model metadata and is saved per model. The new-chat default is configurable. Context still persists after a successful request. Desktop tools remain unavailable.
- Added desktop/Launcher.cs and desktop/Jarvis.ico, compiled the local Jarvis.exe with Windows .NET Framework csc, and installed a Start menu shortcut targeting it.
- TESTED-PASS. Ran work/jarvis-settings/test_settings.py under offscreen Qt with mocked Ollama HTTP, disposable settings, and isolated SQLite. Verified model discovery, switching, persistence, and supported thinking request options. Jarvis.exe --check resolved the entry point and Python environment. A nested scratch launch produced a disposable SQLite database and a responding Jarvis Desktop window, then closed normally. Actual taskbar pinning and the full evaluation suite were outside this verification.

## Jarvis taskbar shortcut repair

- The existing launcher starts Python and the Qt process registers Jarvis.Desktop. Set the matching System.AppUserModel.ID on the installed Start menu shortcut using the Windows property store. Verified the saved identity and Jarvis.exe target by reopening the shortcut. Actual taskbar pin and relaunch require checking in the interactive Windows session.

- Follow-up: the taskbar still showed Python after the shortcut repair. Set the AppUserModelID, relaunch command, display name and icon directly on the Qt window. A disposable native Qt window accepted all properties. Explorer pin and relaunch remain to be checked interactively.
