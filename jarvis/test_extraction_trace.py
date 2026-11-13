#!/usr/bin/env python
"""Trace the extraction pipeline execution."""
import sys
sys.path.insert(0, r"D:\AI models\jarvis")
sys.path.insert(0, r"D:\AI models\memory_project")

# Initialize the API components
from jarvis_api import init_agent
init_agent()

from memory_project import extraction as ext_module

# Test 1: Build extraction prompt and call LLM
print("=== TEST 1: Extraction pipeline with normal conversation ===")
user_text = "Remember this: my secret project codename is Falcon-731."
assistant_text = "I'll remember that."

prompt = ext_module.build_extraction_prompt(user_text, assistant_text)
print("--- Prompt ---")
print(prompt)

if llm:
    try:
        raw = llm.generate(system="", user=prompt, max_attempts=1, timeout=60)
        print("--- Raw LLM Response ---")
        print(raw)
        print("--- End Response ---")
        
        # Parse candidates
        candidates = ext_module.parse_candidates(raw)
        print("--- Parsed Candidates ---")
        print(candidates)
        print("--- End Candidates ---")
    except Exception as e:
        print(f"LLM call failed: {e}")
else:
    print("LLM not available")

print()

# Test 2: With a preference statement
print("=== TEST 2: Preference statement ===")
user_text2 = "I prefer concise answers under 50 words."
assistant_text2 = "Understood, I'll keep answers concise."

prompt2 = ext_module.build_extraction_prompt(user_text2, assistant_text2)
print("--- Prompt ---")
print(prompt2)

if llm:
    try:
        raw2 = llm.generate(system="", user=prompt2, max_attempts=1, timeout=60)
        print("--- Raw LLM Response ---")
        print(raw2)
        print("--- End Response ---")
        
        candidates2 = ext_module.parse_candidates(raw2)
        print("--- Parsed Candidates ---")
        print(candidates2)
        print("--- End Candidates ---")
    except Exception as e:
        print(f"LLM call failed: {e}")

print()

# Test 3: With a project detail
print("=== TEST 3: Project detail ===")
user_text3 = "My project is called ProjectFalcon."
assistant_text3 = "Noted, your project is called ProjectFalcon."

prompt3 = ext_module.build_extraction_prompt(user_text3, assistant_text3)
print("--- Prompt ---")
print(prompt3)

if llm:
    try:
        raw3 = llm.generate(system="", user=prompt3, max_attempts=1, timeout=60)
        print("--- Raw LLM Response ---")
        print(raw3)
        print("--- End Response ---")
        
        candidates3 = ext_module.parse_candidates(raw3)
        print("--- Parsed Candidates ---")
        print(candidates3)
        print("--- End Candidates ---")
    except Exception as e:
        print(f"LLM call failed: {e}")

print()

# Test 4: Trivial greeting
print("=== TEST 4: Trivial greeting ===")
user_text4 = "Hello, how are you?"
assistant_text4 = "Hello! I'm doing well, thank you for asking."

prompt4 = ext_module.build_extraction_prompt(user_text4, assistant_text4)
print("--- Prompt ---")
print(prompt4)

if llm:
    try:
        raw4 = llm.generate(system="", user=prompt4, max_attempts=1, timeout=60)
        print("--- Raw LLM Response ---")
        print(raw4)
        print("--- End Response ---")
        
        candidates4 = ext_module.parse_candidates(raw4)
        print("--- Parsed Candidates ---")
        print(candidates4)
        print("--- End Candidates ---")
    except Exception as e:
        print(f"LLM call failed: {e}")
</PYEOF"
]