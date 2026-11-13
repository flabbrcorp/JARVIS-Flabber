# Technology Context: Jarvis

## Environment
- **OS**: Windows (verified) + cross-platform capable
- **Python**: 3.x (specific version C:\Python39\python.exe per policy)
- **Working Directory**: D:\AI models\jarvis

## Dependencies
- **Standard Library**: os, re, sqlite3, time, json, pathlib, typing
- **Third-Party**: requests (for LLM API connectivity)
- **No framework lock-in**: Pure Python, no Flask/Django/FastAPI required for core

## LLM Setup
- **Local Model**: Qwen3.8-27B-Uncensored.gguf
- **Inference Engine**: LM Studio or Ollama
- **Endpoint**: http://127.0.0.1:8129/v1 (configurable via JARVIS_LLM_URL env)
- **Model Path**: D:\AI models\orcarouter_Qwen3.8-27B-Uncensored-IQ2_M.gguf (default, configurable)

## Memory System
- **Database**: memory.db (SQLite, default in working dir)
- **Override**: MEMORY_DB environment variable
- **Tables**: episodes, memories, lessons, memories_fts (FTS5 virtual table)
- **Search**: BM25-ranked FTS5 keyword search

## Configuration Files
- **config.json**: tavily_api_key, default_timeout, max_file_size_kb
- **policy.json**: dangerous patterns, allowed paths, limits, allowed tools
- **jarvis.env**: Environment variables (JARVIS_LLM_URL, JARVIS_LLM_MODEL, JARVIS_LLM_API_KEY)

## Permissions (from .claude/settings.json)
- **Allowed Read**: C:\Users\{USER}\Desktop, C:\Users\{USER}\Documents, D:\AI models\JARVIS
- **Allowed Write**: C:\Users\{USER}\Documents\JARVIS_LOGS
- **Allowed Execute**: C:\Python39\python.exe
- **Denied**: jarvis.env, .env files, rm/del commands, git push/checkout

## Models Available (in D:\AI models)
- Nemotron-3.5-Lightning-30B-A3B-UD-Q4_K_M.gguf
- orcarouter_Qwen3.8-27B-Uncensored-IQ2_M.gguf
- Multiple Qwen3.8 and Ornith model variants