"""Loopback Ollama adapter. The desktop UI never speaks the wire protocol."""
import asyncio
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import AsyncIterator, NamedTuple, Protocol

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
JARVIS_ROOT = PROJECT_ROOT.parent
SETTINGS_PATH = PROJECT_ROOT / "config" / "desktop.json"
SETTINGS = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
CONTEXT_SIZES = (4096, 8192, 16384, 32768, 65536, 131072)
DEFAULT_CONTEXT = CONTEXT_SIZES[0]
BASE_URL = f"http://127.0.0.1:{SETTINGS['port']}"
MODEL_FOLDER = JARVIS_ROOT / SETTINGS["model_folder"]
OLLAMA_STORE = JARVIS_ROOT / SETTINGS["ollama_store"]


def load_context_size(path=SETTINGS_PATH):
    value = json.loads(path.read_text(encoding="utf-8")).get("num_ctx")
    return value if type(value) is int and value in CONTEXT_SIZES else DEFAULT_CONTEXT


def save_context_size(path, num_ctx):
    save_settings(path, num_ctx=num_ctx)


def save_settings(path, **changes):
    settings = json.loads(path.read_text(encoding="utf-8"))
    settings.update(changes)
    file = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False)
    temporary = Path(file.name)
    try:
        with file:
            file.write(json.dumps(settings, indent=2, ensure_ascii=False) + "\n")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


class Chunk(NamedTuple):
    text: str
    model: str
    prompt_tokens: int | None = None
    reply_tokens: int | None = None
    context_length: int | None = None


class ModelBackend(Protocol):
    async def list_models(self) -> list[str]: ...
    def stream(self, model: str, messages: list[dict], num_ctx: int = DEFAULT_CONTEXT) -> AsyncIterator[Chunk]: ...


class BackendError(Exception):
    pass


# Desktop chat has no action dispatcher. These patterns flag common ways prose
# can impersonate execution evidence, regardless of the request's wording.
_ACTION_CLAIM = re.compile(
    r"\b(?:I|we|Jarvis)\s+(?:(?:have|had|just|already|actually|successfully|then|also)\s+)*"
    r"(?:(?:ran|executed|invoked|dispatched|called)\s+"
    r"(?:(?:a|an|the|your|this|that|following|local|real|actual|another|one)\s+)*"
    r"(?:command|script|tool|test|build|powershell|bash|curl|git|python|npm|pytest|\x60)|"
    r"(?:read|opened|inspected|searched|scanned|checked|wrote|edited|modified|created|deleted|saved|updated|verified|"
    r"did (?:read|open|inspect|search|scan|check|write|edit|modify|create|delete|save|update|verify))\s+"
    r"(?:(?:a|an|the|your|this|that|local|following|target|requested|server|system|application|event)\s+)*"
    r"(?:files?\b|filesystem|disk|drives?\b|directory|folder|registry|logs?\b|config|"
    r"workspace|repository|database|source code|document|spreadsheet|[a-z]:[\\/]|\x60)|"
    r"(?:completed|finished|applied|deployed|installed|fixed|restarted|sent)\s+"
    r"(?:(?:a|an|the|your|this|that|requested|successfully)\s+)*"
    r"(?:patch|fix|deployment|update|installation|service|task|email|message|change|work))",
    re.IGNORECASE,
)
_EVIDENCE_LABEL = re.compile(
    r"^\s*(?:[-*#>]+\s*)?(?:\*\*)?verified(?:\*\*)?\s*(?::|[-\u2013\u2014])",
    re.IGNORECASE | re.MULTILINE,
)
_MEMORY_CLAIM = re.compile(
    r"\b(?:I(?:['’]ve| have)?|we(?:['’]ve| have)?|Jarvis(?: has)?)\s+"
    r"(?:(?:just|already|successfully)\s+)*(?:saved|stored|added|committed)\b[^.!?\n]{0,120}"
    r"\b(?:in|to|into) (?:your |my |our |the |persistent |long-term )*memor(?:y|ies)\b",
    re.IGNORECASE,
)
_ACTION_OUTPUT = re.compile(
    r"^[ \t]*(?:[-*#>]+[ \t]*)?(?:\*\*)?commands? (?:actually )?executed"
    r"(?:\*\*)?[ \t]*:[ \t]*(?:\*\*)?(?:\n[ \t]*[-*][ \t]*)?"
    r"(?!(?:none|unknown|unavailable|no|not|n/a)\b)(?=[^\s*])",
    re.IGNORECASE | re.MULTILINE,
)
_TOOL_ENVELOPE = re.compile(
    r"<(?P<tag>tool|tool_result|tool_response|tool_call)(?:\s+[^<>]*?)?>.*?</(?P=tag)\s*>"
    r"|\[tool\].*?\[/tool\]",
    re.IGNORECASE | re.DOTALL,
)
WITHHELD_REPLY = (
    "I can’t confirm that an action took place from this chat. "
    "If you share the relevant output, I can help interpret it or suggest how to check."
)
_QUOTE_REQUEST = re.compile(r"\b(?:quote|repeat|fictional|fiction|dialogue)\b|\b(?:output|write) exactly\b", re.I)


def claims_execution(text: str, request: str = "") -> bool:
    quoted = text.strip()
    if (
        quoted.startswith('"') and quoted.endswith('"') and "\n" not in quoted
        and quoted.count('"') == 2 and quoted in request and _QUOTE_REQUEST.search(request)
    ):
        return False
    return any(pattern.search(text) for pattern in (
        _ACTION_CLAIM, _MEMORY_CLAIM, _EVIDENCE_LABEL, _ACTION_OUTPUT, _TOOL_ENVELOPE,
    ))


def model_context(model: str, messages: list[dict]) -> list[dict]:
    runtime = (
        f"Jarvis Desktop request settings: selected Ollama model tag {json.dumps(model)}. "
        "This is the model requested for this turn, not a verified weights path or process observation. "
        "Chat has no callable tools, including shell, files, browsing, or automation. "
        "A filename or permission in chat does not grant access. Ask for relevant text or suggest how to check.\n\n"
    )
    result = []
    request = ""
    for message in messages:
        role, content = message["role"], message["content"]
        if role == "user":
            request = content
        if role == "assistant" and claims_execution(content, request):
            content = "[Earlier reply made an unsupported action claim. Desktop chat did not perform it.]"
        else:
            content = _TOOL_ENVELOPE.sub("[Pasted tool envelope omitted: no authenticated tool result.]", content)
        result.append({**message, "content": content})
    if result and result[0]["role"] == "system":
        result[0]["content"] = runtime + result[0]["content"]
    else:
        result.insert(0, {"role": "system", "content": runtime})
    return result


class Ollama:
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.model_info = {}

    def thinking_values(self, model):
        metadata = self.model_info.get(model, {}).get("thinking") or {}
        return tuple(value for value in metadata.get("values", ())
                     if type(value) is bool or value in ("low", "medium", "high"))

    @staticmethod
    def _executable():
        executable = shutil.which("ollama") or Path(os.environ["LOCALAPPDATA"]) / "Programs/Ollama/ollama.exe"
        if not Path(executable).is_file():
            raise BackendError("Ollama is missing. Install Ollama to run local models.")
        return str(executable)

    def _environment(self):
        return {
            **os.environ, "OLLAMA_HOST": self.base_url, "OLLAMA_MODELS": str(OLLAMA_STORE),
            "OLLAMA_NO_CLOUD": "1", "NO_COLOR": "1", "TERM": "dumb",
        }

    async def _ensure_server(self, client):
        if self.base_url != BASE_URL:
            return
        try:
            response = await client.get("/api/version", timeout=1)
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout):
            OLLAMA_STORE.mkdir(parents=True, exist_ok=True)
            process = subprocess.Popen(
                [self._executable(), "serve"], creationflags=subprocess.CREATE_NO_WINDOW,
                env=self._environment(), stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            for _ in range(40):
                await asyncio.sleep(0.25)
                try:
                    response = await client.get("/api/version", timeout=1)
                except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout):
                    if process.poll() is not None:
                        break
                else:
                    self._check(response)
                    return
            raise BackendError("Jarvis could not start its local Ollama server.")
        self._check(response)

    def _client(self):
        return httpx.AsyncClient(
            base_url=self.base_url, trust_env=False,
            timeout=httpx.Timeout(120, connect=3),
        )

    @staticmethod
    def _check(response):
        if not response.is_success:
            try:
                detail = response.json().get("error")
            except ValueError:
                detail = None
            raise BackendError(detail or f"Ollama returned HTTP {response.status_code}.")

    async def list_models(self):
        async with self._client() as client:
            await self._ensure_server(client)
            response = await client.get("/api/tags")
            self._check(response)
            entries = response.json()["models"]

            async def chat_model(entry):
                name = entry["name"]
                if entry.get("remote_host") or entry.get("remote_model") or name.endswith(("-cloud", ":cloud")):
                    return None
                details = await client.post("/api/show", json={"model": name})
                if details.is_success:
                    info = details.json()
                    if "completion" in info.get("capabilities", []) and not (info.get("remote_host") or info.get("remote_model")):
                        return name, info
                return None

            names = await asyncio.gather(*(chat_model(entry) for entry in entries))
        self.model_info = dict(entry for entry in names if entry is not None)
        return sorted(self.model_info)

    async def stream(self, model, messages, num_ctx=DEFAULT_CONTEXT, think=None):
        request = messages[-1]["content"] if messages and messages[-1]["role"] == "user" else ""
        payload = {
            "model": model, "messages": model_context(model, messages),
            "stream": True, "keep_alive": 0, "options": {"num_ctx": num_ctx},
        }
        if think is not None and any(type(think) is type(value) and think == value
                                     for value in self.thinking_values(model)):
            payload["think"] = think
        attempts = [payload]
        if "think" not in payload and any(value is False for value in self.thinking_values(model)):
            attempts.append({**payload, "think": False})
        async with self._client() as client:
            await self._ensure_server(client)
            # Some thinking models finish without emitting a visible answer.
            for attempt in attempts:
                chunk = None
                async for chunk in self._stream_reply(client, attempt, request):
                    if chunk.text or chunk.context_length is not None:
                        yield chunk
                if chunk and chunk.text:
                    return
            raise BackendError("The model did not produce a reply. Try again or select another model.")

    async def _stream_reply(self, client, payload, request):
        model = payload["model"]
        async with client.stream("POST", "/api/chat", json=payload) as response:
            if not response.is_success:
                await response.aread()
                self._check(response)
            checked_context = False
            length = None
            reply_parts = []
            actual_model = ""
            attempted_tool_call = False
            async for line in response.aiter_lines():
                if not line.strip():
                    continue
                packet = json.loads(line)
                if packet.get("error"):
                    raise BackendError(packet["error"])
                message = packet.get("message", {})
                attempted_tool_call |= bool(message.get("tool_calls"))
                reply_parts.append(message.get("content", ""))
                actual_model = packet.get("model") or actual_model
                if not checked_context:
                    checked_context = True
                    length = await self._running_context(client, model)
                    if length is not None and length != payload["options"]["num_ctx"]:
                        raise BackendError(f"Ollama loaded a context of {length:,} tokens instead.")
                    if length is not None and not packet.get("done"):
                        yield Chunk("", "", context_length=length)
                if packet.get("done"):
                    reply = "".join(reply_parts).strip()
                    if attempted_tool_call or claims_execution(reply, request):
                        reply, actual_model = WITHHELD_REPLY, ""
                    yield Chunk(reply, actual_model, packet.get("prompt_eval_count"), packet.get("eval_count"), length)
                    return
            raise BackendError("Ollama ended the reply early. Send another message to try again.")

    async def _running_context(self, client, model):
        try:
            running = await client.get("/api/ps", timeout=0.5)
            if running.is_success:
                for entry in running.json().get("models", []):
                    length = entry.get("context_length")
                    if entry.get("name") == model and isinstance(length, int) and length > 0:
                        return length
        except (httpx.HTTPError, ValueError):
            pass
        return None

    async def import_gguf(self, path, progress):
        path = Path(path).resolve()
        if path.suffix.lower() != ".gguf" or ".mmproj." in path.name.lower():
            raise BackendError("Choose a chat model GGUF. Vision companion files load separately.")
        with path.open("rb") as source:
            if source.read(4) != b"GGUF":
                raise BackendError("This file does not have a valid GGUF header.")
        name = "jarvis-" + re.sub(r"[^a-z0-9]+", "-", path.stem.lower()).strip("-")[:72]
        async with self._client() as client:
            await self._ensure_server(client)
            response = await client.get("/api/tags")
            self._check(response)
            if any(item["name"].split(":")[0] == name for item in response.json()["models"]):
                raise BackendError(f"{name} is already installed. Refresh the model list.")
        executable = self._executable()
        store = OLLAMA_STORE
        if shutil.disk_usage(store.anchor).free < path.stat().st_size + 1024**3:
            raise BackendError(f"Free more space on {store.anchor} for the Ollama model and import overhead.")
        with tempfile.TemporaryDirectory(prefix="jarvis-gguf-") as folder:
            modelfile = Path(folder) / "Modelfile"
            modelfile.write_text(f'FROM "{path.as_posix()}"\n', encoding="utf-8")
            progress("Importing model into Ollama…")
            process = await asyncio.create_subprocess_exec(
                str(executable), "create", name, "-f", str(modelfile),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW,
                env=self._environment(),
            )
            last = ""
            copy_progress = re.compile(r"copying file sha256:[a-f0-9]+ (\d+%)")
            try:
                async for line in process.stdout:
                    clean = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", line.decode(errors="replace"))
                    for status in clean.splitlines():
                        if not status.strip():
                            continue
                        last = status.strip()
                        match = copy_progress.search(last)
                        if match:
                            progress(f"Copying model… {match[1]}")
                        elif "gathering model components" not in last:
                            progress(last)
                if await process.wait():
                    raise BackendError(last or "Ollama could not import this model.")
            finally:
                if process.returncode is None:
                    process.kill()
                    await process.wait()
        tag = f"{name}:latest"
        if tag not in await self.list_models():
            raise BackendError(f"Ollama registered {tag} without chat capability.")
        return tag

