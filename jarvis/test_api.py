"""Test script for Jarvis API on port 8130."""
import requests
import json
import os

BASE = "http://127.0.0.1:8130"
API_KEY = os.environ.get("JARVIS_LLM_API_KEY", "")

print(f"API Key present: {bool(API_KEY)}")
print(f"BASE: {BASE}")
print()

# Test 1: Check models endpoint
print("=" * 50)
print("Test 1: Models endpoint")
print("=" * 50)
resp = requests.get(f"{BASE}/v1/models", 
                    headers={"Authorization": f"Bearer {API_KEY}"})
print(f"Status: {resp.status_code}")
data = resp.json()
models_data = data.get("data", [])
print(f"Models in response: {len(models_data)}")
jarvis_meta = data.get("_jarvis_meta", {})
print(f"Jarvis agent connected: {jarvis_meta.get('agent_connected', False)}")
print(f"API version: {jarvis_meta.get('api_version', 'N/A')}")
print()

# Test 2: Chat completion
print("=" * 50)
print("Test 2: Chat completion - Hello")
print("=" * 50)
resp = requests.post(f"{BASE}/v1/chat/completions", 
                     headers={"Authorization": f"Bearer {API_KEY}"},
                     json={"messages": [{"role": "user", "content": "Hello, how are you?"]})
print(f"Status: {resp.status_code}")
data = resp.json()
choice = data.get("choices", [{}])[0]
message = choice.get("message", {})
content = message.get("content", "NO RESPONSE")
print(f"Assistant response: {content[:200]}")
jarvis_meta = data.get("_jarvis_meta", {})
print(f"Agent connected: {jarvis_meta.get('agent_connected', False)}")
print(f"Memory count: {jarvis_meta.get('memory_count', 'N/A')}")
print(f"Tool iterations: {jarvis_meta.get('tool_iterations', 'N/A')}")
print()

# Test 3: Another message (memory test)
print("=" * 50)
print("Test 3: Chat completion - set_task")
print("=" * 50)
resp = requests.post(f"{BASE}/v1/chat/completions", 
                     headers={"Authorization": f"Bearer {API_KEY}"},
                     json={"messages": [{"role": "user", "content": "set_task: remember my RTX 3090"}]})
print(f"Status: {resp.status_code}")
data = resp.json()
choice = data.get("choices", [{}])[0]
message = choice.get("message", {})
content = message.get("content", "NO RESPONSE")
print(f"Assistant response: {content[:200]}")
print()

# Test 4: Another message (memory recall)
print("=" * 50)
print("Test 4: Chat completion - recall task")
print("=" * 50)
resp = requests.post(f"{BASE}/v1/chat/completions", 
                     headers={"Authorization": f"Bearer {API_KEY}"},
                     json={"messages": [{"role": "user", "content": "what is my task"}]})
print(f"Status: {resp.status_code}")
data = resp.json()
choice = data.get("choices", [{}])[0]
message = choice.get("message", {})
content = message.get("content", "NO RESPONSE")
print(f"Assistant response: {content[:200]}")
print()

print("=" * 50)
print("All tests complete!")
print("=" * 50)