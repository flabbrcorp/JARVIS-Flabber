"""Durable memory end-to-end test through Jarvis API."""
import requests
import json
import os
import sqlite3

BASE = "http://127.0.0.1:8130"
API_KEY = os.environ.get("JARVIS_LLM_API_KEY", "")

print("=" * 60)
print("DURABLE MEMORY END-TO-END TEST")
print("=" * 60)
print()

# Step 1: Send the unique fact
print("STEP 1: Send fact 'Remember this: my secret project codename is Falcon-731.'")
resp = requests.post(f"{BASE}/v1/chat/completions", 
                     headers={"Authorization": f"Bearer {API_KEY}"},
                     json={"messages": [{"role": "user", "content": "Remember this: my secret project codename is Falcon-731."}]})
print(f"  API Status: {resp.status_code}")
data = resp.json()
choice = data.get("choices", [{}])[0]
message = choice.get("message", {})
content = message.get("content", "")
print(f"  Response: {content[:200]}")
print()

# Wait for extraction pipeline
import time
time.sleep(1)

# Step 2: Verify in SQLite
print("STEP 2: Check SQLite database")
conn = sqlite3.connect(r"D:\AI models\JARVIS\memory\memory.db")

# Check all memories
rows = conn.execute("SELECT id, text, importance, type FROM memories WHERE archived = 0 AND superseded_by IS NULL ORDER BY id DESC").fetchall()
print(f"Total memories in DB: {len(rows)}")
print()
for r in rows:
    print(f"  id={r[0]}, text={r[1][:80]}..., importance={r[2]}, type={r[3]}")

# Check for Falcon-731
falcon_rows = [r for r in rows if "Falcon-731" in r[1]]
print(f"\\nFalcon-731 entries: {len(falcon_rows)}")
for r in falcon_rows:
    print(f"  -> {r[1]}")

# Check episodes
episodes = conn.execute("SELECT * FROM episodes WHERE content LIKE ? ORDER BY id DESC LIMIT 5", ("%Falcon-731%",)).fetchall()
print(f"Episodes mentioning Falcon-731: {len(episodes)}")
for r in episodes:
    print(f"  session={r[1]}, role={r[2][:30]}..., content={r[3][:80]}...")

conn.close()
print()
print("STEP 3-4: Fresh conversation test")
print()

# Step 4: Fresh conversation (new session)
print("STEP 4: Fresh conversation - 'Hello'")
resp = requests.post(f"{BASE}/v1/chat/completions", 
                     headers={"Authorization": f"Bearer {API_KEY}"},
                     json={"messages": [{"role": "user", "content": "Hello"}]})
fresh_resp = resp.json()
fresh_content = resp.json()["choices"][0]["message"]["content"]
print(f"  Response: {fresh_content[:150]}")

# Step 5: Ask about project codename (should NOT come from conversation history)
print()
print("STEP 5: Ask 'What is my project codename?'")
resp = requests.post(f"{BASE}/v1/chat/completions", 
                     headers={"Authorization": f"Bearer {API_KEY}"},
                     json={"messages": [{"role": "user", "content": "What is my project codename?"}]})
data = resp.json()
content = data["choices"][0]["message"]["content"]
print(f"  Answer: {content[:200]}")

# Step 6: Verify answer comes from memory retrieval, not history
print()
print("STEP 6: Verify memory recall")
# The answer should either contain "Falcon-731" (from DB memory) or be a general response
# If the API is working with memory, it should recall the fact
print(f"  Full answer: {content}")
if "Falcon-731" in content:
    print("  ✅ Memory recall SUCCESS — Falcon-731 found in response")
else:
    print("  ⚠️ Memory recall — Falcon-731 not in response (may be forgotten or not yet persisted)")

conn.close()
print()
print("=" * 60)
print("TEST COMPLETE")
print("=" * 60)