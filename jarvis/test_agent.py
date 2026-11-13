#!/usr/bin/env python
"""Test JARVIS agent directly."""
import sys
sys.path.insert(0, '.')

from agent import Agent
from config import load_policy
import os

# Set policy
policy = load_policy()
print(f"Policy loaded: {policy.get('allowed_tools', [])}")
print()

# Test 1: shell_execute
agent = Agent()
response = agent.handle_request("run Get-Process -Name python")
print("=== TEST 1: run Get-Process -Name python ===")
print(response)
print()

# Test 2: file_list
response = agent.handle_request("list D:\\AI models\\JARVIS")
print("=== TEST 2: list D:\\AI models\\JARVIS ===")
print(response)
print()

# Test 3: file_read
response = agent.handle_request("read D:\\AI models\\JARVIS\\policy.json")
print("=== TEST 3: read policy.json ===")
print(response)
print()

# Test 4: file_write
response = agent.handle_request("write D:\\AI models\\JARVIS\\test_output.txt:Hello from JARVIS")
print("=== TEST 4: write test_output.txt ===")
print(response)
print()

# Test 5: verify write
response = agent.handle_request("read D:\\AI models\\JARVIS\\test_output.txt")
print("=== TEST 5: verify write ===")
print(response)
print()

# Test 6: web_search (will fail without API key, but tests the flow)
response = agent.handle_request("search JARVIS AI")
print("=== TEST 6: web_search ===")
print(response)
print()

# Test 7: set_task
response = agent.handle_request("set_task: Write a Python script to scrape a webpage")
print("=== TEST 7: set_task ===")
print(response)
print()

# Test 8: shell_execute with active task
response = agent.handle_request("run dir")
print("=== TEST 8: run dir (with task set) ===")
print(response)
print()

print("All tests complete!")