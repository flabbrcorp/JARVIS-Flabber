"""JARVIS Agent — the core daemon for tool-request handling."""
import sys
import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8')

from tools import shell_read, shell_execute, file_read, file_write, file_list, file_search, web_search, web_fetch
from config import load_config, load_policy, save_config, set_policy
import jarvis_memory as memory_mod
from Jarvis import LocalLLM

MEMORY_DB = str(Path(__file__).resolve().parent / "memory" / "memory.db")

# Make memory_project modules importable (core_memory, extraction, retrieval, jarvis_resume)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "memory_project"))

import extraction
import retrieval
import core_memory
import jarvis_resume

# Max tool-calling iterations per user turn — prevents infinite loops
MAX_TOOL_ITERATIONS = 5

# System prompt that tells Qwen how to behave and what tools are available
SYSTEM_PROMPT = """You are JARVIS, a local AI assistant running on the user's machine.

You have access to tools. When a user request requires a tool, respond with a JSON object:
{"tool": "<tool_name>", "args": {"<arg_key>": "<arg_value>"}}

When the user is just chatting, greeting you, or asking a question that doesn't need a tool, respond with:
{"tool": null, "answer": "<your direct response>"}

Available tools:
- file_read: read a file. Args: {"path": "<file_path>"}
- file_write: write to a file. Args: {"path": "<file_path>", "content": "<content>"}
- file_list: list directory contents. Args: {"path": "<folder_path>"}
- file_search: search for files. Args: {"path": "<folder_path>", "pattern": "<pattern>"}
- shell_execute: run a shell command. Args: {"command": "<command>"}
- shell_read: read shell output. Args: {"path": "<file_path>", "limit": 100}
- web_search: search the web. Args: {"query": "<search_query>"}
- web_fetch: fetch a URL. Args: {"url": "<url>"}

Examples:
User: hello -> {"tool": null, "answer": "Hello! How can I help you today?"}
User: what's your name? -> {"tool": null, "answer": "I'm JARVIS, your local assistant."}
User: read config.py -> {"tool": "file_read", "args": {"path": "config.py"}}
User: list the JARVIS folder -> {"tool": "file_list", "args": {"path": "D:\\AI models\\JARVIS"}}

Rules:
- Only call one tool per turn unless the user explicitly asks for multiple steps.
- If the user is just chatting or asking a general question, set tool to null and answer directly.
- Never output anything other than the JSON object.
- Be concise and direct."""

# Default policy if none exists
DEFAULT_POLICY = {
    "version": "1.0",
    "dangerous_patterns": [
        "rm -rf", "del /f /s /q", "format", "sudo -i",
        "certutil decode", "powershell -enc", "eval\\("
    ],
    "allowed_paths": {
        "read": ["C:\\Users\\{USER}\\Desktop", "C:\\Users\\{USER}\\Documents", "D:\\AI models\\JARVIS"],
        "write": ["C:\\Users\\{USER}\\Documents\\JARVIS_LOGS"],
        "execute": ["C:\\Python39\\python.exe", "C:\\Users\\{USER}\\AppData\\Local\\Programs\\Python\\Python39\\python.exe"],
    },
    "limits": {"timeout": 120, "max_processes": 10, "max_file_size_kb": 102400},
    "allowed_tools": [
        "shell_read", "shell_execute", "file_read", "file_write",
        "file_list", "file_search", "web_search", "web_fetch"
    ],
}


class Agent:
    """The agent that processes requests and coordinates tool calls."""

    def __init__(self, state: Optional[dict] = None):
        self.config = load_config()
        self.policy = load_policy()
        self.current_task = None
        self.active_objectives: List[Dict[str, Any]] = []
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

        # Initialize the local LLM (Qwen via LU Local API)
        self.llm = LocalLLM()
        self._llm_connected = False
        try:
            self._llm_connected = self.llm.connect(check=False)
        except Exception:
            self._llm_connected = False

        # Build resume brief from previous sessions (memory + memory.md)
        self.resume_brief = ""
        try:
            self.resume_brief = jarvis_resume.build_resume_brief(
                memory_md=str(Path(__file__).resolve().parent / "memory.md"),
                db_path=MEMORY_DB,
                current_session=self.session_id,
                max_chars=1500,
                recent_turns=6,
                log_lines=5,
                top_memories=5,
            )
        except Exception:
            self.resume_brief = ""

        # Initialize state if not provided
        if state is None:
            state = self._load_state()

        self.current_task = state.get("task", None)
        if self.current_task:
            self.current_task["status"] = state.get("status", "idle")
            self.current_task["created_at"] = state.get("created_at", datetime.now().isoformat())
            self.current_task["steps_completed"] = state.get("steps_completed", [])
            self.current_task["current_step"] = state.get("current_step")

    def _load_state(self) -> dict:
        """Load state from file."""
        state_path = "state/current_task.json"
        import os
        import json
        if os.path.exists(state_path):
            with open(state_path, "r") as f:
                return json.load(f)
        return {"status": "idle", "task": "", "created_at": datetime.now().isoformat()}

    def _save_state(self, state: dict):
        """Save state to file."""
        state_path = "state/current_task.json"
        import os
        os.makedirs(os.path.dirname(state_path), exist_ok=True)
        with open(state_path, "w") as f:
            json.dump(state, f, indent=2)

    def handle_request(self, request: str) -> str:
        """Main entry point for processing a request.

        Runs a bounded observe-act loop: Qwen picks a tool, we execute it,
        feed the result back to Qwen, and repeat until Qwen gives a final
        answer or MAX_TOOL_ITERATIONS is reached.
        """
        start_time = time.time()

        # Log incoming user request
        try:
            user_episode_id = memory_mod.log_episode(
                self.session_id, "user", request, db_path=MEMORY_DB
            )
        except Exception:
            user_episode_id = None

        # Build memory-augmented system prompt (resume brief + scored memories)
        system_prompt = self._build_system_prompt(request)

        tool_calls: List[Dict] = []
        tool_results: List[str] = []
        final_answer = None

        for iteration in range(MAX_TOOL_ITERATIONS):
            # Step 1: Parse and validate — try LLM first, fall back to keyword router
            parsed = None
            if self._llm_connected:
                try:
                    if iteration == 0:
                        parsed = self._llm_route(request, system_prompt=system_prompt)
                    else:
                        parsed = self._llm_route_with_tool_result(
                            request, tool_results[-1], system_prompt=system_prompt
                        )
                except Exception:
                    parsed = None
            if parsed is None:
                if iteration == 0:
                    parsed = self._parse_request(request)
                else:
                    # Fallback on iteration > 0: treat last result as final answer
                    parsed = {"valid": True, "tool": None, "answer": tool_results[-1]}

            if not parsed.get("valid"):
                response = f"❌ Error: {parsed.get('error', 'Unknown error')}"
                try:
                    memory_mod.log_episode(self.session_id, "assistant", response, db_path=MEMORY_DB)
                except Exception:
                    extract_and_store(user_text, assistant_text, llm_fn, source_episode, db_path)
                return response

            # Handle direct answer from LLM (no tool needed)
            tool = parsed.get("tool")
            if tool is None:
                answer = parsed.get("answer", "I'm not sure how to help with that.")
                final_answer = answer
                response = f"[{datetime.now().strftime('%H:%M:%S')}] {answer}"
                self._log_conversation(request, response, tool_calls, tool_results)
                try:
                    memory_mod.log_episode(self.session_id, "assistant", response, db_path=MEMORY_DB)
                except Exception:
                    pass
                # Extract durable facts from this turn
                try:
                    extraction.extract_and_store(
                        user_text=request,
                        assistant_text=answer,
                        llm_fn=lambda p: self.llm.generate(
                            system=system_prompt, user=p,
                            max_attempts=1, timeout=60,
                        ),
                        source_episode=user_episode_id,
                        db_path=MEMORY_DB,
                    )
                except Exception:
                    pass
                return response

            # Step 2: Check tool access
            if not self._authorize_tool(tool):
                response = f"❌ Access denied: '{tool}' is not in your allowed tools list."
                try:
                    memory_mod.log_episode(self.session_id, "assistant", response, db_path=MEMORY_DB)
                except Exception:
                    pass
                return response

            # Step 3: Check context
            if not self._check_context(parsed):
                response = f"❌ Context unavailable: {parsed.get('context_error', '')}"
                try:
                    memory_mod.log_episode(self.session_id, "assistant", response, db_path=MEMORY_DB)
                except Exception:
                    pass
                return response

            # Step 4: Execute the tool
            result = self._execute_tool(tool, parsed)
            tool_calls.append(parsed)
            tool_results.append(result)

        # Max iterations reached — force a final answer from the last result
        last_result = tool_results[-1] if tool_results else "no result produced"
        final_answer = last_result
        response = f"[{datetime.now().strftime('%H:%M:%S')}] Reached {MAX_TOOL_ITERATIONS} tool steps. Last result: {last_result}"
        self._log_conversation(request, response, tool_calls, tool_results)
        try:
            memory_mod.log_episode(self.session_id, "assistant", response, db_path=MEMORY_DB)
        except Exception:
            pass
        # Extract durable facts from this turn
        try:
            extraction.extract_and_store(
                user_text=request,
                assistant_text=final_answer,
                llm_fn=lambda p: self.llm.generate(
                    system=system_prompt, user=p,
                    max_attempts=1, timeout=60,
                ),
                source_episode=user_episode_id,
                db_path=MEMORY_DB,
            )
        except Exception:
            pass
        return response

    def _llm_route_with_tool_result(self, request: str, last_tool_result: str, system_prompt: str = SYSTEM_PROMPT) -> Dict[str, Any]:
        """Ask Qwen what to do next after seeing a tool result.

        Returns a parsed dict (same shape as _llm_route).
        """
        user_prompt = f"""User request: {request}

Previous tool result:
{last_tool_result}

Based on this result, what's next? Respond with a JSON object only:
- {{"tool": null, "answer": "<final answer>"}} if you have enough information
- {{"tool": "<tool_name>", "args": {{...}}}} if another tool is needed"""

        raw = self.llm.generate(
            system=system_prompt,
            user=user_prompt,
            max_attempts=1,
            timeout=60,
        )
        if raw is None:
            raise RuntimeError("LLM returned no response")

        # Try to parse the JSON response
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise RuntimeError("LLM response contains no JSON object")

        try:
            data = json.loads(raw[start:end + 1])
        except json.JSONDecodeError:
            raise RuntimeError("LLM response is not valid JSON")

        tool = data.get("tool")
        if tool is None:
            answer = data.get("answer", "I'm not sure how to help with that.")
            return {"valid": True, "tool": None, "answer": answer}

        if tool not in self.policy.get("allowed_tools", []):
            raise RuntimeError(f"LLM requested unauthorized tool: {tool}")

        args = data.get("args", {})
        if not isinstance(args, dict):
            args = {}

        return {"valid": True, "tool": tool, "args": args}

    def _parse_request(self, request: str) -> Dict[str, Any]:
        """Parse a natural language request into structured intent."""
        request_lower = request.strip().lower()

        # Detect tool intent - check in order of specificity
        # file_write (highest priority - needs special handling)
        if "write" in request_lower:
            parts = request_lower.split("write", 1)
            path_part = parts[0].strip()
            content_part = parts[1].strip() if len(parts) > 1 else ""
            # Try to extract path (remove "write" prefix)
            path = path_part.replace("write", "").strip()
            return {"valid": True, "tool": "file_write", "args": {"path": path, "content": content_part}}

        # shell_execute - if it starts with "run " or "do " or just a command
        if request_lower.startswith("run ") or request_lower.startswith("do "):
            return {
                "valid": True,
                "tool": "shell_execute",
                "args": {"command": request.split()[1]},
            }
        elif "run" in request_lower:
            return {
                "valid": True,
                "tool": "shell_execute",
                "args": {"command": request.split("run ")[-1].strip()},
            }

        # file_read - "read <path>" or "show me <path>" or "what is <path>"
        if "read" in request_lower:
            parts = request_lower.split("read", 1)
            path = parts[1].strip() if len(parts) > 1 else ""
            return {"valid": True, "tool": "file_read", "args": {"path": path}}
        elif "show me" in request_lower:
            path = request_lower.split("show me", 1)[1].strip()
            return {"valid": True, "tool": "file_read", "args": {"path": path}}
        elif "what is" in request_lower:
            path = request_lower.split("what is", 1)[1].strip()
            return {"valid": True, "tool": "file_read", "args": {"path": path}}

        # file_list - "list <path>" or "ls <path>" or "folder <path>"
        if "list" in request_lower:
            parts = request_lower.split("list", 1)
            path = parts[1].strip() if len(parts) > 1 else ""
            return {"valid": True, "tool": "file_list", "args": {"path": path}}
        elif "ls" in request_lower:
            parts = request_lower.split("ls", 1)
            path = parts[1].strip() if len(parts) > 1 else ""
            return {"valid": True, "tool": "file_list", "args": {"path": path}}
        elif "folder" in request_lower:
            parts = request_lower.split("folder", 1)
            path = parts[1].strip() if len(parts) > 1 else ""
            return {"valid": True, "tool": "file_list", "args": {"path": path}}

        # web_search
        if "search" in request_lower:
            parts = request_lower.split("search", 1)
            query = parts[1].strip() if len(parts) > 1 else ""
            return {"valid": True, "tool": "web_search", "args": {"query": query}}

        # web_fetch
        if "fetch" in request_lower:
            parts = request_lower.split("fetch", 1)
            url = parts[1].strip() if len(parts) > 1 else ""
            return {"valid": True, "tool": "web_fetch", "args": {"url": url}}

        # file_search
        if "search" in request_lower and "file" in request_lower:
            parts = request_lower.split("search", 1)
            rest = parts[1].strip()
            if "file" in rest:
                file_part = rest.split("file", 1)[1].strip()
                pattern_part = rest.split("for", 1)[1].strip()
                return {"valid": True, "tool": "file_search", "args": {"path": file_part, "pattern": pattern_part}}

        # Default: treat as a request to execute a command
        return {
            "valid": True,
            "tool": "shell_execute",
            "args": {"command": request},
        }

    def _build_system_prompt(self, request: str) -> str:
        """Build the system prompt with resume brief + relevant memories injected.

        Combines:
        1. Base SYSTEM_PROMPT
        2. Resume brief (from previous sessions + memory.md)
        3. Top-k relevant memories retrieved via scored_search

        This keeps context token-efficient: only relevant memories are sent,
        not the full conversation history.
        """
        blocks = [SYSTEM_PROMPT]

        # 1. Resume brief (who the user is, where we left off)
        if self.resume_brief:
            blocks.append("\n## Resume Brief\n" + self.resume_brief)

        # 2. Relevant memories from scored retrieval
        try:
            relevant = retrieval.scored_search(
                request, limit=5, candidates=20, db_path=MEMORY_DB
            )
        except Exception:
            relevant = []

        if relevant:
            mem_lines = []
            for m in relevant:
                mem_lines.append(f"- {m['text']} (importance={m['importance']}, confidence={m['confidence']:.2f})")
            blocks.append("\n## Remembered Facts\n" + "\n".join(mem_lines))

        return "\n".join(blocks)

    def _llm_route(self, request: str, system_prompt: str = SYSTEM_PROMPT) -> Dict[str, Any]:
        """Ask Qwen to decide what to do. Returns a parsed dict or raises on failure."""
        user_prompt = f"""User request: {request}

Respond with a JSON object only:
- {{"tool": null, "answer": "<direct response>"}} if no tool is needed
- {{"tool": "<tool_name>", "args": {{...}}}} if a tool is needed"""

        raw = self.llm.generate(
            system=system_prompt,
            user=user_prompt,
            max_attempts=1,
            timeout=60,
        )
        if raw is None:
            raise RuntimeError("LLM returned no response")

        # Try to parse the JSON response
        raw = raw.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

        # Find the JSON object
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise RuntimeError("LLM response contains no JSON object")

        try:
            data = json.loads(raw[start:end + 1])
        except json.JSONDecodeError:
            raise RuntimeError("LLM response is not valid JSON")

        tool = data.get("tool")
        if tool is None:
            # Direct answer, no tool needed
            answer = data.get("answer", "I'm not sure how to help with that.")
            return {"valid": True, "tool": None, "answer": answer}

        if tool not in self.policy.get("allowed_tools", []):
            raise RuntimeError(f"LLM requested unauthorized tool: {tool}")

        args = data.get("args", {})
        if not isinstance(args, dict):
            args = {}

        return {"valid": True, "tool": tool, "args": args}

    def _authorize_tool(self, tool: str) -> bool:
        """Check if the tool is in the user's allowed list."""
        allowed = self.policy.get("allowed_tools", [])
        return tool in allowed

    def _check_context(self, parsed: Dict[str, Any]) -> bool:
        """Check if the agent has the necessary context."""
        # Allow shell_execute and file_write without a task set
        # Only require context for file_search and web_search
        if not self.current_task and parsed.get("tool") in ("file_search", "web_search"):
            error = "You must set an active task using 'set_task: <objective>' before searching."
            self._log_feedback("context_check", "failed", f"Agent needs an active task. Try: set_task: <your objective>")
            return False
        return True

    def _execute_tool(self, tool: str, parsed: Dict[str, Any]) -> str:
        """Execute the requested tool with its arguments."""
        try:
            if tool == "shell_execute":
                return shell_execute(parsed["args"]["command"])
            elif tool == "shell_read":
                return shell_read(parsed["args"]["path"], parsed["args"].get("limit", 100))
            elif tool == "file_read":
                return file_read(parsed["args"]["path"])
            elif tool == "file_write":
                return file_write(parsed["args"]["path"], parsed["args"]["content"])
            elif tool == "file_list":
                return file_list(
                    parsed["args"]["path"],
                    parsed["args"].get("recursive", False),
                    parsed["args"].get("pattern")
                )
            elif tool == "file_search":
                return file_search(parsed["args"]["path"], parsed["args"]["pattern"], parsed["args"].get("max_results", 50))
            elif tool == "web_search":
                return web_search(parsed["args"]["query"], parsed["args"].get("max_results", 5))
            elif tool == "web_fetch":
                return web_fetch(parsed["args"]["url"], parsed["args"].get("max_length", 24000))
        except Exception as e:
            return f"Tool execution failed: {e}"

    def _format_response(self, result: str, start_time: float) -> str:
        """Format the tool result into a user-friendly response."""
        elapsed = time.time() - start_time
        timestamp = datetime.now().strftime("%H:%M:%S")

        if elapsed > 10:
            return f"[{timestamp}] TIME: {elapsed:.1f}s | {result}"
        else:
            return f"[{timestamp}] {result}"

    def _log_conversation(self, user_input: str, response: str, tool_calls: List[Dict], tool_results: List[str]):
        """Log the conversation to the history file."""
        import os
        import json
        from datetime import datetime
        log_path = "memory/conversation_history.jsonl"
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        entry = {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "model_response": response,
            "tool_calls": tool_calls,
            "tool_results": tool_results,
        }
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def _log_feedback(self, task: str, evaluation: str, notes: str):
        """Log feedback to the feedback file."""
        import os
        import json
        from datetime import datetime
        log_path = "memory/feedback.jsonl"
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        entry = {
            "timestamp": datetime.now().isoformat(),
            "task": task,
            "evaluation": evaluation,
            "notes": notes,
        }
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def set_task(self, objective: str) -> str:
        """Set an active task for the agent."""
        self.current_task = {
            "objective": objective,
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "steps_completed": [],
            "current_step": None,
        }
        self._save_state(self.current_task)
        self._log_objective_update(objective, "active")
        return f"✅ Task set: '{objective}'"

    def step(self, description: str) -> str:
        """Mark a step as completed in the current task."""
        if self.current_task:
            self.current_task["steps_completed"].append(description)
            self.current_task["current_step"] = description
            self.current_task["updated_at"] = datetime.now().isoformat()
            self._save_state(self.current_task)
            return f"✅ Step completed: {description}"
        return "No active task set. Use 'set_task: <objective>' first."

    def _log_objective_update(self, objective: str, status: str):
        """Log an objective update."""
        import os
        import json
        log_path = "memory/objective_log.jsonl"
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        entry = {
            "timestamp": datetime.now().isoformat(),
            "objective": objective,
            "status": status,
        }
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def get_current_task(self) -> Optional[dict]:
        """Get the current active task."""
        return self.current_task

    def set_policy(self, policy: dict):
        """Set the policy from a dictionary."""
        set_policy(policy)
        self.policy = policy
        return "✅ Policy updated."

    def set_policy_file(self, path: str):
        """Set the policy from a file path."""
        set_policy_file(path)
        self.policy = load_policy()
        return "✅ Policy loaded from file."

    async def run(self):
        """Run the agent in a loop."""
        while True:
            request = input("JARVIS> ").strip()
            if not request:
                continue
            if request.lower() == "exit":
                print("Goodbye.")
                break
            response = self.handle_request(request)
            print(response)
            print()


def main():
    """Run the agent in a loop."""
    import os
    import json
    state = None
    if os.path.exists("state/current_task.json"):
        with open("state/current_task.json") as f:
            state = json.load(f)

    agent = Agent(state)

    print("\n" + "=" * 50)
    print("  JARVIS Agent v0.1.0")
    print("=" * 50)
    print("  Commands:")
    print("    run <command>           — execute a shell command")
    print("    read <file>             — read a file")
    print("    write <path>:<content>  — write to a file")
    print("    list <folder>           — list directory contents")
    print("    search <query>          — search the web")
    print("    fetch <url>             — fetch a URL")
    print("    searchfile <path> <pattern> — search files")
    print("    set_task: <objective>   — set an active task")
    print("    exit                    — stop the agent")
    print("=" * 50 + "\n")

    while True:
        try:
            request = input("JARVIS> ").strip()
            if not request:
                continue
            if request.lower() == "exit":
                print("Goodbye.")
                break
            response = agent.handle_request(request)
            print(response)
            print()
        except KeyboardInterrupt:
            print("\nGoodbye.")
            break
        except EOFError:
            print("\nGoodbye.")
            break


if __name__ == "__main__":
    main()