# Memory Bank Instructions

## Purpose
This memory bank maintains project context and development continuity across Cline sessions. It captures the project's architecture, decisions, and status so that future sessions can pick up where the last one left off.

## Required Reading
At the start of every new task, read the following files in this order:
1. `memory-bank/projectBrief.md` - Project purpose and goals
2. `memory-bank/systemPatterns.md` - Architecture and design decisions
3. `memory-bank/techContext.md` - Technologies, environment, dependencies
4. `memory-bank/activeContext.md` - Current focus and immediate next steps
5. `memory-bank/progress.md` - Completed work and outstanding items
6. `memory-bank/decisions.md` - Important decisions and rationale

After significant development, discoveries, corrections, or decisions, update the relevant files.

## Preservation Rules
- **Do NOT replace, restructure, or modify** the existing Jarvis memory architecture (`memory.py`, `memory.md`, episode/memory tables)
- These Memory Bank files are SEPARATE and supplement (not replace) the existing system
- Only update files when there are meaningful changes worth preserving
- Keep entries concise and accurate; avoid duplicating source code

## Update Triggers
Update Memory Bank files when:
- New architecture decisions are made
- Dependencies or environment changes
- Significant code changes or additions
- Bug fixes that change behavior
- User instruction updates
- Configuration changes

## Directory Structure
```
.d/clinerules/
├── memory-bank.md    (these instructions)
└── memory-bank/
    ├── projectBrief.md
    ├── systemPatterns.md
    ├── techContext.md
    ├── activeContext.md
    ├── progress.md
    └── decisions.md
```