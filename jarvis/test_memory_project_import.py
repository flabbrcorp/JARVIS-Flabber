import sys
import os
# Use forward slashes - Python on Windows handles these
sys.path.insert(0, "D:/AI models/jarvis")

from memory_project import extraction
from memory_project import retrieval
from memory_project import core_memory

print("All memory_project modules imported successfully")

# Test extraction.build_extraction_prompt
prompt = extraction.build_extraction_prompt(
    'Remember this: my secret project codename is Falcon-731.',
    "I'll remember that."
)
print(f"Prompt built: {len(prompt)} chars")

# Test extraction.parse_candidates
test_json = '[{"text": "my secret project codename is Falcon-731", "type": "project", "importance": 9}]'
result = extraction.parse_candidates(test_json)
print(f"Parsed candidates: {result}")

# Test no JSON
result2 = extraction.parse_candidates("I'll remember that, okay?")
print(f"No JSON candidates: {result2}")

# Test retrieval.scored_search
import jarvis_memory as mm
mm.DEFAULT_DB = "D:/AI models/jarvis/memory/test_memory_temp.db"
mm.init_db("D:/AI models/jarvis/memory/test_memory_temp.db")

# Add a test memory
test_id = mm.add_memory(
    text="my secret project codename is Falcon-731",
    type="project",
    importance=9
)
print(f"Added test memory ID: {test_id}")

# Test scored_search
results = retrieval.scored_search("Falcon-731", limit=5)
print(f"Scored search results: {len(results)}")
for r in results[:3]:
    print(f"  - {r.get('text', '')[:80]}... score: {r.get('score', 'N/A')}")