# Jarvis shared development journal

Codex and Cline use this journal to coordinate work on Jarvis. Flab owns project priorities and approves architectural changes. The journal records evidence and ownership. Check it against the current checkout and runtime before relying on it.

- [CURRENT_STATE.md](CURRENT_STATE.md) records the verified baseline, current milestone, active work, and limitations.
- [DECISIONS.md](DECISIONS.md) records significant decisions and their approval status.
- [OPEN_ISSUES.md](OPEN_ISSUES.md) tracks unresolved problems, owners, and verification.
- [CHANGELOG.md](CHANGELOG.md) records meaningful work in date order and links to evidence.
- [Codex's journal](agents/CODEX.md) and [Cline's journal](agents/CLINE.md) hold each contributor's own work notes.

## Session workflow

1. Read this file, [CURRENT_STATE.md](CURRENT_STATE.md), and [OPEN_ISSUES.md](OPEN_ISSUES.md). Review recent [CHANGELOG.md](CHANGELOG.md) entries, relevant [DECISIONS.md](DECISIONS.md) entries, and both agent journals for prior work or overlap.
2. Check Git status and verify important claims against the code, runtime, or an executed test. If a journal entry disagrees with the code, record both observations and the evidence for each. Check ownership before touching a shared component. Record active work and its owner in Current State when coordination is needed.
3. Work within the assignment. Record significant discoveries, failed attempts, and outstanding questions. If another agent is working on the same files, coordinate the handoff before editing. If agents disagree, record both positions with evidence and leave the issue unresolved for Flab's review.
4. Update your own journal after meaningful work. Record files touched, rationale, failures, test commands and outcomes, evidence or commit IDs, and follow-up. Update the changelog and any related issue. Update Current State only with supported findings. Record architecture proposals as `PROPOSED` and mark decisions `APPROVED` only with explicit approval.
5. Re-read the latest on-disk copy just before updating a shared file and preserve concurrent edits. Leave a dated correction or cross-reference for a disputed or superseded entry. Preserve other agents' journals and historical records.

## Evidence and issue status

| Label | Meaning |
|---|---|
| VERIFIED | Directly supported by named source code, observed output, or executed tests. State whether the evidence covers implementation or runtime behavior. |
| INFERRED | Evidence supports a conclusion that has yet to be established directly. |
| UNKNOWN | Available evidence is insufficient. |
| PROPOSED | Suggested work awaiting implementation and any needed approval. |
| IMPLEMENTED-UNTESTED | The change exists and successful behavior has yet to be verified. |
| TESTED-PASS / TESTED-FAIL | An executed test with its command, environment, and actual outcome recorded. |

Check existing issues before creating an ID. Include component, severity, impact, evidence, reproduction steps when available, owner or unassigned, and related changes or tests. Use `SUSPECTED`, `CONFIRMED`, `INVESTIGATING`, `FIXED-UNVERIFIED`, or `VERIFIED-RESOLVED`. Resolve a previously assigned issue using direct evidence and coordination with its owner.

## Existing records and Git

The [Desktop README](../jarvis/desktop/README.md) documents Desktop usage. Cline's [Memory Bank instructions](../jarvis/.clinerules/memory-bank.md) and [existing Memory Bank](../jarvis/.clinerules/memory-bank/) provide historical context, especially for the legacy agent and its memory stack. Link to relevant material and keep shared status in this journal. Confirm the scope of earlier claims before carrying them forward. [CLAUDE.md](../jarvis/CLAUDE.md) records Claude-specific priorities. Ask Flab to resolve any priority conflict that affects the assigned work.

The journal has its own local Git repository at `D:\AI_JARVIS\development`. The application repository is at `D:\AI_JARVIS\jarvis`. Use `git -C D:\AI_JARVIS\development status --short` for journal files and the source repository for code. Review the staged diff before committing. Stage only journal documents and their ignore policy. Keep secrets, private transcripts, databases, model files, and generated artifacts outside Git. Reference evidence by path or commit and include the command and outcome needed to interpret it.
