"""Verify agent.py imports and parses correctly."""
import ast
with open("agent.py", "r", encoding="utf-8") as f:
    source = f.read()
ast.parse(source)
print("Syntax OK")

# Try importing Agent
import sys
sys.path.insert(0, ".")
from agent import Agent, SYSTEM_PROMPT
print("Agent imported OK")
print("SYSTEM_PROMPT length:", len(SYSTEM_PROMPT))

agent = Agent()
print("Agent instantiated OK")
print("LLM connected:", agent._llm_connected)
agent.llm.close()