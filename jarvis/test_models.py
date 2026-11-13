import os
"""List models available on LU port 8129."""
import sys
sys.path.insert(0, r"D:\AI models\jarvis")
from Jarvis import LocalLLM

llm = LocalLLM(
    url="http://127.0.0.1:8129/v1",
    model="ignored",
    api_key=os.environ.get("JARVIS_LLM_API_KEY", ""),
)
resp = llm.session.get(f"{llm.base_url}/models", headers=llm._build_headers(), timeout=10)
print(resp.status_code)
print(resp.text[:2000])
llm.close()