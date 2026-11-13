# Decisions: Jarvis

## Architecture Decisions

### 1. SQLite over JSON/JSONL
- **Why**: Concurrent access safety, built-in querying (SQL), zero dependencies
- **When**: Phase 1 memory implementation (memory.py)
- **Alternative considered**: JSON files, but no native querying or transaction safety

### 2. FTS5 + Triggers for Search
- **Why**: BM25 ranking, automatic index sync, no external search library needed
- **When**: Integrated with memories table via triggers
- **Alternative considered**: Separate search index, but requires manual sync

### 3. Three-Table Design (episodes + memories + lessons)
- **Why**: Separation of concerns - episodes = conversation history, memories = facts/knowledge, lessons = trigger-action patterns
- **When**: Initial design, still active
- **Alternative considered**: Single flat memory, but lacks structured evolution

### 4. Importance (1-10) + Confidence (0-1) Scoring
- **Why**: Prioritize important facts, distinguish certainty level
- **When**: Memory design from the start
- **Alternative considered**: Simple true/false, but loses nuance

### 5. Superseded/Archived Memory Management
- **Why**: Prevent memory clutter, allow evolution of facts
- **When**: Designed into schema from beginning
- **Mechanics**: superseded_by FK, archived flag, FTS query filtering

### 6. Local-First, Zero-API-Key LLM
- **Why**: Privacy, cost control, offline capability, no rate limits
- **When**: Initial project design
- **Model**: Qwen3.8-27B.gguf via LM Studio/Ollama
- **Alternative considered**: OpenAI/API-based, but rejected for privacy/cost

## Design Pattern Decisions

### 7. Context Manager Pattern (_connect in memory.py)
- **Why**: Consistent connection handling, automatic cleanup, foreign keys enabled
- **When**: All memory operations go through this context manager
- **Pattern**: Yield-commit-close in finally block

### 8. Environment Variable Configuration
- **Why**: Flexible deployment, no code changes for different setups
- **Variables**: MEMORY_DB, JARVIS_LLM_URL, JARVIS_LLM_MODEL, JARVIS_LLM_API_KEY
- **Default**: Sensible defaults for out-of-the-box experience

### 9. Memory Importance Threshold (importance 1-10, default 5)
- **Why**: Balance between capturing everything and noise
- **When**: add_memory() function validates range
- **Alternative**: Unlimited range, but 1-10 is intuitive

### 10. Session Isolation (session_id in episodes)
- **Why**: Multiple concurrent conversations don't mix
- **When**: log_episode() requires session_id
- **Alternative**: Global memory, but loses session boundaries

## User Experience Decisions

### 11. Memory.md as Primary Session Notes File
- **Why**: Human-readable, survives restarts, explicit standing rules
- **When**: 2026-10-28 session start, folded from GPT context prompt
- **Content**: Identity, user goals, standing rules, session protocol

### 12. UNCONFIRMED Markers for Unverified Claims
- **Why**: Prevent hallucination propagation, user awareness
- **When**: Hardware specs, any fact not explicitly verified
- **Pattern**: **UNCONFIRMED** text in memory.md

### 13. Confirm Before Irreversible Actions
- **Why**: User safety, prevent accidental data loss
- **When**: Standing rules, before delete/send/spend actions
- **Pattern**: Explicit user confirmation required

## Decisions Preserved from Original System
- Existing memory.py schema NOT modified (per task constraint)
- memory.md content preserved and augmented
- SQLite database structure unchanged
- Existing model configuration respected
- **Cline session JSON access**: File located at `C:\Users\flab\.cline\data\sessions\1793700258668_vh7sh\1793700258668_vh7sh.messages.json` (1.9 MB) but cannot be directly parsed due to directory access restrictions (outside allowed path: D:\AI models\jarvis)
- **Conversation export**: Saved to `d:\AI models\jarvis\conversation_export.txt` summarizing current session topics and decisions
- **Memory Bank creation**: Successfully initialized .clinerules/ directory with 6 files (projectBrief, systemPatterns, techContext, activeContext, progress, decisions)
- **Session protocol**: Established "read Memory Bank files at start of each task" requirement