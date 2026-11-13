"""llm_ping.py - sends ONE test message to the local model and prints the reply.

Run from the JARVIS folder while Locally Uncensored has the model loaded:
    python llm_ping.py
"""
import sys

sys.stdout.reconfigure(encoding="utf-8")

from Jarvis import LocalLLM

llm = LocalLLM()
print("URL:  ", llm.base_url)
print("MODEL:", llm.model)
if llm.connect():
    reply = llm.generate(
        "You are a connection test. Follow the instruction exactly.",
        "Reply with exactly: ready",
        max_attempts=1,
        timeout=120,
    )
    print("REPLY:", reply)
llm.close()
