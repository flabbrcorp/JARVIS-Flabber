#!/usr/bin/env python
"""Diagnostic extraction pipeline — does NOT modify original modules."""
import sys
import json

# Add project roots
sys.path.insert(0, r"D:\AI models\jarvis")
sys.path.insert(0, r"D:\AI models\memory_project")

from Jarvis import LocalLLM
from jarvis_api import init_agent
from memory_project import extraction as ext_module

# Initialize
init_agent()

# Test messages
user_text = "Remember this: my secret project codename is Falcon-731."
assistant_text = "I'll remember that."

# Build prompt
prompt = ext_module.build_extraction_prompt(user_text, assistant_text)
print("=== EXTRACTION PROMPT ===")
print(prompt)

# Run extraction with diagnostics
llm = init_agent()  # This gets the llm from the API setup
# Actually we need the llm from the API, let me just test the pipeline components separately

print("\n=== TESTING parse_candidates ===")
# Test parse_candidates with valid JSON
test_json = '[{"text": "Falcon-731 project", "type": "project", "importance": 9}]'
result = ext_module.parse_candidates(test_json)
print(f"Valid JSON candidates: {result}")

# Test with no JSON
test_no_json = "I'll remember that, okay?"
result2 = ext_module.parse_candidates(test_no_json)
print(f"No JSON candidates: {result2}")

print("\n=== EXTRACTION PROMPT ===")
print(prompt)