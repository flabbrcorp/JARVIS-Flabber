"""Milestone 2 — Integration audit test.

Traces an incoming request through jarvis_api.py → agent.py → memory modules.
Records what actually executes and what gets persisted to the SQLite database.
"""
import sys
import os
import json
import time
import threading
import requests
from pathlib import Path

# Add paths
sys.path.insert(0, r"D:\AI models\jarvis")
sys.path.insert(0, r"D:\AI models\memory_project")

from Jarvis import LocalLLM
import jarvis_memory as memory_mod
import extraction
import retrieval
import core_memory
import jarvis_resume

# Configuration
BASE = "http://127.0.0.1:8130"
API_KEY = os.environ.get("JARVIS_LLM_API_KEY", "")
MEMORY_DB = r"D:\AI models\JARVIS\memory\memory.db"

# Results tracking
results = {
    "resume_brief_built": False,
    "memories_retrieved": 0,
    "facts_extracted": 0,
    "tool_calls": 0,
    "api_errors": [],
}

# In-memory conversation tracking
conversation_history = []


def get_jarvis_api():
    """Ensure API server is running."""
    # API server should already be running from prior test
    return BASE


def test_connection():
    """Test 1: Verify API is running."""
    try:
        resp = requests.get(f"{BASE}/v1/models", 
                            headers={"Authorization": f"Bearer {API_KEY}"})
        results["api_errors"].append(f"Connection: {resp.status_code}")
        return resp.status_code == 200
    except Exception as e:
        results["api_errors"].append(f"Connection error: {e}")
        return False


def test_chat(message, label):
    """Test incoming message through the API.

    Traces: API → agent._llm_route → system_prompt (with resume brief + memories)
             → possible extraction.extract_and_store → possible agent._execute_tool
    """
    print(f"\n--- Test: {label} ---")
    try:
        resp = requests.post(f"{BASE}/v1/chat/completions", 
                             headers={"Authorization": f"Bearer {API_KEY}"},
                             json={"messages": [{"role": "user", "content": message}]},
                             timeout=60)
        
        if resp.status_code != 200:
            results["api_errors"].append(f"{label}: status {resp.status_code}")
            print(f"  HTTP error: {resp.status_code}")
            return
        
        data = resp.json()
        choice = data.get("choices", [{}])[0]
        message_resp = choice.get("message", {})
        content = message_resp.get("content", "")
        
        print(f"  Response: {content[:150]}...")
        
        # Check jarvis_meta for agent involvement
        meta = data.get("_jarvis_meta", {})
        results["resume_brief_built"] = results["resume_brief_built"] or meta.get("agent_connected", False)
        results["memories_retrieved"] = results["memories_retrieved"] or (meta.get("memory_count", 0) > 0)
        results["tool_calls"] = results["tool_calls"] or (meta.get("tool_iterations", 0) > 0)
        
        # Store conversation for memory testing
        conversation_history.append(("user", message))
        conversation_history.append(("assistant", content))
        
    except Exception as e:
        results["api_errors"].append(f"{label}: {e}")
        print(f"  Error: {e}")


def test_memory_persistence():
    """Test memory persistence in SQLite.

    Checks that the conversation and any extracted facts are stored."""
    print(f"\n--- Test: Memory Persistence ---")
    try:
        with memory_mod._connect(MEMORY_DB) as conn:
            # Check recent episodes (conversation history)
            rows = conn.execute(
                "SELECT * FROM episodes ORDER BY id DESC LIMIT 4"
            ).fetchall()
            print(f"  Recent episodes in DB: {len(rows)}")
            for row in rows:
                print(f"    - {row['role']}: {row['content'][:60]}...")
            
            # Check memories (fact extraction results)
            rows2 = conn.execute(
                "SELECT text, importance, importance FROM memories WHERE archived = 0 AND superseded_by IS NULL ORDER BY importance DESC LIMIT 5"
            ).fetchall()
            results["memories_retrieved"] = len(rows2) > 0
            print(f"  Facts/ memories in DB: {len(rows2)}")
            for row in rows2[:3]:
                print(f"    - {row['text'][:60]}... (importance={row['importance']})")
    except Exception as e:
        results["api_errors"].append(f"DB error: {e}")
        print(f"  Database error: {e}")


def main():
    """Run the full integration audit."""
    print("=" * 60)
    print("MILESTONE 2 — INTEGRATION AUDIT")
    print("=" * 60)
    print()
    
    # Verify API connection
    print("Testing API connection...")
    if not test_connection():
        results["api_errors"].append("Failed to connect to API server")
        print_results()
        return
    
    # Test conversations that should trigger different features
    test_chat("Hello, how are you?", "greeting")
    test_chat("set_task: my project X", "set_task")
    test_chat("what is my task?", "recall_task")
    
    # Test memory persistence in SQLite
    test_memory_persistence()
    
    # Report
    print_results()


def print_results():
    print("\n" + "=" * 60)
    print("MILESTONE 2 — INTEGRATION AUDIT RESULTS")
    print("=" * 60)
    print(f"Resume brief built: {results['resume_brief_built']}")
    print(f"Memories retrieved from DB: {results['memories_retrieved']}")
    print(f"API errors: {len(results['api_errors'])}")
    for e in results["api_errors"]:
        print(f"  - {e}")
    print("=" * 60)


if __name__ == "__main__":
    main()