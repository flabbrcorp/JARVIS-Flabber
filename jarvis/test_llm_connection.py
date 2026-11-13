import os
"""Quick test: verify LocalLLM connects to LU on port 8129 with the API key."""
import sys
sys.path.insert(0, r"D:\AI models\jarvis")
from Jarvis import LocalLLM

llm = LocalLLM(
    url="http://127.0.0.1:8129/v1",
    model=r"lu/D:\AI models\orcarouter_Qwen3.8-27B-Uncensored-IQ2_M.gguf",
    api_key=os.environ.get("JARVIS_LLM_API_KEY", ""),
)

print("URL:  ", llm.base_url)
print("MODEL:", llm.model)
if llm.connect(check=False):
    reply = llm.generate(
        "You are a connection test.",
        "Reply with exactly: ready",
        max_attempts=1,
        timeout=60,
    )
    print("REPLY:", reply)
llm.close()