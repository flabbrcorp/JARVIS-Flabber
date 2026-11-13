"""Verify agent.py syntax after Phase 3 changes."""
import ast
with open("agent.py", "r", encoding="utf-8") as f:
    source = f.read()
ast.parse(source)
print("Syntax OK")

import sys
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "memory_project"))

from agent import Agent, MAX_TOOL_ITERATIONS
print(f"MAX_TOOL_ITERATIONS = {MAX_TOOL_ITERATIONS}")

agent = Agent()
print("Agent instantiated OK")
print("LLM connected:", agent._llm_connected)
print("Resume brief length:", len(agent.resume_brief))
if agent.resume_brief:
    print("Resume brief preview:", agent.resume_brief[:200])
agent.llm.close()
agent.llm.close()