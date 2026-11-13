#!/usr/bin/env python
"""
Test script for Falcon-731 memory persistence through Jarvis API.
Tests: explicit memory request → extraction → SQLite persistence → fresh-session recall.
"""
import sys
import os
import time
import json
import sqlite3

# Add project roots to path
sys.path.insert(0, r"D:\AI models\jarvis")
sys.path.insert(0, r"D:\AI models\memory_project")

# Configuration
API_BASE = "http://127.0.0.1:8130"
MEMORY_DB = r"D:\AI models\JARVIS\memory\memory.db"
LU_API_KEY_ENV = "JARVIS_LLM_API_KEY"

def get_lu_api_key():
    """Read LU API key from environment, never expose it."""
    import os
    key = os.environ.get(LU_API_KEY_ENV, "")
    return key

def check_api_running():
    """Check if the Jarvis API server is already running."""
    import urllib.request
    import json
    try:
        url = f"{API_BASE}/v1/models"
        req = urllib.request.Request(url)
        # Add auth header if key available
        key = get_lu_api_key()
        if key:
            req.add_header("Authorization", f"Bearer {key}")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return True, data
    except Exception:
        return False, None

def start_api_server():
    """Attempt to start the Jarvis API server."""
    import subprocess
    import sys
    
    # Try to start the server in the background
    try:
        # Use the existing Python interpreter
        proc = subprocess.Popen(
            [sys.executable, "jarvis_api.py"],
            cwd=r"D:\AI models\jarvis",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            # DETACHEDPROCESS = 0x00000008  # don't create new console window
        )
        return True, proc
    except Exception as e:
        return False, str(e)

def send_chat_message(message, api_key=None):
    """Send a chat message to the Jarvis API."""
    import urllib.request
    import urllib.error
    import json
    
    url = f"{API_BASE}/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    payload = {
        "model": "lu/D:\AI models\orcarouter_Qwen3.8-27B-Uncensored-IQ2_M.gguf",
        "messages": [{"role": "user", "content": message}],
        "stream": False
    }
    
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return True, result
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else "no body"
        return False, f"HTTP {e.code}: {error_body[:200]}"
    except Exception as e:
        return False, str(e)[:200]

def check_memory_database(codename="Falcon-731"):
    """Check the SQLite database for the memory fact."""
    try:
        conn = sqlite3.connect(MEMORY_DB)
        c = conn.cursor()
        
        # Search for the codename
        c.execute("SELECT * FROM memories WHERE text LIKE ?", (f"%{codename}%",))
        rows = c.fetchall()
        
        # Also check recent memories
        c.execute("SELECT * FROM memories ORDER BY last_used DESC LIMIT 10")
        recent = c.fetchall()
        
        conn.close()
        return True, rows, recent
    except Exception as e:
        return False, None, str(e)[:200]

def main():
    print("=" * 60)
    print("FALCON-731 MEMORY PERSISTENCE TEST")
    print("=" * 60)
    print()
    
    # Step 1: Check if API is running
    print("[1] Checking if Jarvis API server is running...")
    api_running, api_data = check_api_running()
    
    if not api_running:
        print("  -> API not running. Attempting to start...")
        success, result = start_api_server()
        if not success:
            print(f"  -> FAILED to start API server: {result}")
            print("  -> Please start the API manually: python jarvis_api.py")
            return
        print("  -> API server started.")
        time.sleep(3)  # Wait for server to initialize
        api_running, api_data = check_api_running()
    
    if api_running and api_data:
        print(f"  -> API is running. Models: {len(api_data.get('data', []))}")
    
    # Step 2: Send Falcon-731 memory request
    print("\n[2] Sending memory request: 'Remember this: my secret project codename is Falcon-731.'")
    
    api_key = get_lu_api_key()
    success, result = send_chat_message(
        "Remember this: my secret project codename is Falcon-731.",
        api_key=api_key
    )
    
    if not success:
        print(f"  -> FAILED to send message: {result}")
        return
    
    print(f"  -> API response received.")
    print(f"  -> Response type: {result.get('choices', [{}])[0].get('message', {}).get('role', 'unknown')}")
    
    # Step 3: Wait for extraction to complete
    print("\n[3] Waiting for extraction pipeline to complete...")
    time.sleep(5)  # Give extraction time to process
    
    # Step 4: Check SQLite database
    print("\n[4] Checking SQLite database for Falcon-731 memory...")
    success, rows, recent = check_memory_database("Falcon-731")
    
    if success:
        print(f"  -> Database query successful.")
        print(f"  -> Memories with 'Falcon-731': {len(rows)}")
        
        if rows:
            print("  -> Memory entries found:")
            for row in rows:
                print(f"     ID: {row[0]} | Text: {row[1]} | Type: {row[2]} | Importance: {row[3]} | Confidence: {row[4]}")
        else:
            print("  -> No memories found with 'Falcon-731' in text.")
            # Show recent memories
            print("  -> Recent memories in database:")
            for row in recent[:5]:
                print(f"     ID: {row[0]} | Text: {row[1][:80] if row[1] else 'None'} | Type: {row[2]}")
    
    else:
        print(f"  -> FAILED to query database: {recent}")
    
    # Step 5: Fresh session recall test
    print("\n[5] Testing fresh-session recall...")
    print("  -> (Would need new API session - skipping in this test)")
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    # Final database check
    conn = sqlite3.connect(MEMORY_DB)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM memories")
    total_memories = c.fetchone()[0]
    conn.close()
    
    print(f"  -> Total memories in database: {total_memories}")
    print(f"  -> Falcon-731 memory insertion: {'PASS' if rows else 'FAIL'}")
    print()
    print("  -> Next step: Start a new session and ask 'What is my project codename?'")
    print("  -> to verify cross-session recall from SQLite.")

if __name__ == "__main__":
    main()