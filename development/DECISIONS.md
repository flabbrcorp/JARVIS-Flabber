# Decisions

Use `PROPOSED`, `APPROVED`, `SUPERSEDED`, or `REVERSED`. Include the approval source and any replacement decision. Record alternatives that were actually discussed, or identify them as implementation options assessed by the contributor.

## DEC-001 — Shared development journal

- **Date and status:** 2026-11-12, APPROVED by Flab in the shared development journal setup request.
- **Decision:** Use `D:\AI_JARVIS\development` for shared state, decisions, issues, chronology, and individually owned agent journals. Keep runtime and architecture changes within separately authorized assignments.
- **Reason:** Give contributors a common record of ownership, evidence, and unfinished work.
- **Alternatives assessed by Codex:** Reuse Cline's Memory Bank alone or put the shared files under the source checkout. The former is specific to Cline and includes legacy runtime notes. The latter would change the requested path.
- **Implementation choice:** Use a standalone local journal repository because the existing source repository begins at `jarvis\`. Keep its Git scope to the journal documents and ignore policy. Flab approved the journal and location. Codex selected this Git layout.
