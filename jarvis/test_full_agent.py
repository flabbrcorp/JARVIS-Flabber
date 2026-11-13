"""Full end-to-end test of Agent.handle_request with LLM routing."""
import sys
sys.path.insert(0, ".")
from agent import Agent

agent = Agent()
print("LLM connected:", agent._llm_connected)

# Test 1: Direct question (no tool needed)
print("\n--- Test 1: Direct question ---")
resp = agent.handle_request("Hello, how are you?")
print("Response:", resp)

# Test 2: File read request
print("\n--- Test 2: File read ---")
resp = agent.handle_request("read config.py")
print("Response:", resp[:200] if resp else resp)

# Test 3: List directory
print("\n--- Test 3: List directory ---")
resp = agent.handle_request("list D:\AI models\JARVIS")
print("Response:", resp[:300] if resp else resp)

agent.llm.close()
print("\nAll tests complete.")