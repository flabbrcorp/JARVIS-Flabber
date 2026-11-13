import requests
import time
import os
from pathlib import Path
from typing import Optional, Dict, Any


def _load_env_file(env_path=None):
    """Load key=value pairs from a .env file into os.environ (without overwriting existing vars)."""
    if env_path is None:
        env_path = Path(__file__).resolve().parent / "jarvis.env"
    env_path = Path(env_path)
    if not env_path.is_file():
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = value
    except Exception:
        pass

class LocalLLM:
    """Reliable connection to local Qwen model via LM Studio / Ollama."""

    def __init__(self, url: str = None, model: str = None, api_key: str = None,
                 temperature: float = 0.7, repeat_penalty: float = 1.1,
                 stop_sequences: list = None, top_p: float = 0.9):
        _load_env_file()
        self.base_url = url or os.environ.get("JARVIS_LLM_URL", "http://127.0.0.1:8129/v1")
        self.model = model or os.environ.get("JARVIS_LLM_MODEL", r"lu/D:\AI models\orcarouter_Qwen3.8-27B-Uncensored-IQ2_M.gguf")
        self.api_key = api_key or os.environ.get("JARVIS_LLM_API_KEY", "")
        self.temperature = temperature
        self.repeat_penalty = repeat_penalty
        self.top_p = top_p
        self.stop_sequences = stop_sequences or [
            "<|endoftext|>",
            "\n\nUser:",
            "\n\nAssistant:",
            "\n\nuser:",
            "\n\nassistant:",
        ]
        self.max_retries = 3
        self.retry_delay = 2
        self.timeout = 120
        self.session = requests.Session()
        self._last_error = None
        self._last_response = None

    def _build_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _build_payload(self, system: str, user: str, history: list = None) -> Dict[str, Any]:
        messages = []
        if history:
            messages.extend(history)
        messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})
        return {
            "model": self.model,
            "messages": messages,
            "max_tokens": 8192,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "repeat_penalty": self.repeat_penalty,
            "stop": self.stop_sequences,
        }

    def connect(self, check: bool = True) -> bool:
        """Test the connection and return True if reachable."""
        try:
            response = self.session.get(
                f"{self.base_url}/models",
                headers=self._build_headers(),
                timeout=10
            )
            response.raise_for_status()
            if check:
                models = response.json()
                available = [m["id"] for m in models.get("data", [])]
                if self.model not in available:
                    print(f"⚠️ Model '{self.model}' not found. Available: {available}")
                    return False
            print(f"✅ Connected to {self.base_url} (model: {self.model})")
            return True
        except requests.exceptions.ConnectionError:
            self._last_error = "Cannot connect to LLM server. Is LM Studio / Ollama running?"
            print(f"❌ {self._last_error}")
            return False
        except requests.exceptions.Timeout:
            self._last_error = "Connection timed out. Is the model server responsive?"
            print(f"❌ {self._last_error}")
            return False
        except requests.exceptions.HTTPError as e:
            self._last_error = f"HTTP error: {e.response.text}"
            print(f"❌ {self._last_error}")
            return False

    def generate(self, system: str, user: str, history: list = None,
                 max_attempts: int = 3, timeout: int = 120) -> Optional[str]:
        """Generate a response with automatic retry and timeout handling."""
        for attempt in range(max_attempts):
            try:
                response = self.session.post(
                    f"{self.base_url}/chat/completions",
                    json=self._build_payload(system, user, history),
                    headers=self._build_headers(),
                    timeout=timeout
                )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                self._last_response = content
                self._last_error = None
                print(f"✅ Response received (attempt {attempt + 1})")
                return content.strip()

            except requests.exceptions.ConnectionError:
                self._last_error = f"Connection lost. Retrying in {self.retry_delay}s..."
                print(f"⚠️ {self._last_error}")
                time.sleep(self.retry_delay)
            except requests.exceptions.Timeout:
                self._last_error = f"Generation timed out after {timeout}s. Retrying..."
                print(f"⚠️ {self._last_error}")
                time.sleep(self.retry_delay)
            except requests.exceptions.HTTPError as e:
                self._last_error = f"HTTP error {e.response.status_code}: {e.response.text}"
                print(f"❌ {self._last_error}")
                if attempt == max_attempts - 1:
                    return None
                time.sleep(self.retry_delay)
            except requests.exceptions.JSONDecodeError:
                self._last_error = "Malformed response from model. Trying again..."
                print(f"⚠️ {self._last_error}")
                time.sleep(self.retry_delay)
            except Exception as e:
                self._last_error = f"Unexpected error: {type(e).__name__}: {e}"
                print(f"❌ {self._last_error}")
                return None

        return None

    def get_history(self, system: str, user: str) -> list:
        """Return the conversation history in the format expected by the model."""
        history = [
            {"role": "system", "content": system}
        ]
        history.append({"role": "user", "content": user})
        return history

    def close(self):
        """Close the connection pool."""
        self.session.close()