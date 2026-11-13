# System Patterns: Jarvis

## Architecture Overview
- **Local LLM**: Qwen3.8-27B via LM Studio/Ollama (no API keys required)
- **Memory Layer**: SQLite-backed (memory.py) with three tables:
  - `episodes`: conversation turns per session
  - `memories`: facts with importance, confidence, type tracking
  - `lessons`: trigger-action patterns with strength scoring
- **FTS5 Search**: Full-text search on memories via virtual table + triggers

## Data Flow
1. User input → log as episode → extract facts → add as memories
2. Memory search → BM25 ranking → inject into LLM context
3. LLM response → potentially add new memories/facts

## Memory Tables Design
- **episodes**: session_id, timestamp, role (user/assistant), content
- **memories**: text, type (fact/preference/legacy), importance (1-10), confidence (0-1), source_episode FK, superseded_by FK, archived flag
- **lessons**: trigger text, action text, timestamp, strength (1.0 default)

## Key Design Decisions
- FTS5 with custom triggers keeps search index in sync
- Importance/confidence scoring prioritizes relevant memories
- Superseded/archived memory management prevents clutter
- SQLite chosen for local-first, zero-dependency approach

## LLM Integration
- System prompt includes relevant memories from search
- Episode history provides conversation context
- Memory context injected based on query relevance