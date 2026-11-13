"""Jarvis API — Local HTTP server exposing OpenAI-compatible chat completions.

Routes requests through the existing JARVIS agent (loop cap, memory, tool execution)
and forwards model inference to the LU local API on port 8129.

Usage:
    python jarvis_api.py

The API serves at http://127.0.0.1:8130/v1/... compatible with OpenAI format.

IMPORTANT: Before running, ensure:
- LU Local API is running on port 8129 (with valid API key)
- The LU API key is configured in jarvis.env as JARVIS_LLM_API_KEY
- The JARVIS agent LLM connection works (python main.py)
"""

import json
import sys
import os
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# Add project roots to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "memory_project"))

from agent import Agent, MAX_TOOL_ITERATIONS, SYSTEM_PROMPT
from Jarvis import LocalLLM
import jarvis_memory as memory_mod
import extraction
import retrieval
import core_memory
import jarvis_resume

# Configuration
JARVIS_API_PORT = 8130
LU_API_BASE = "http://127.0.0.1:8129"
MEMORY_DB = str(Path(__file__).resolve().parent / "memory" / "memory.db")

# Global agent instance
agent = None
llm = None


def init_agent():
    """Initialize the JARVIS agent and LLM connection."""
    global agent, llm
    try:
        agent = Agent()
        llm = agent.llm
        print(f"✅ JARVIS Agent initialized, LLM connected: {agent._llm_connected}")
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
        agent = None
        llm = None


class JarvisAPIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the Jarvis API."""

    def _send_json(self, status_code, data):
        """Send a JSON response."""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def _read_body(self):
        """Read the request body content length."""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            return self.rfile.read(content_length)
        return b""

    def _parse_json_body(self):
        """Parse the request body as JSON."""
        try:
            body = self._read_body()
            if body:
                return json.loads(body.decode("utf-8"))
            return {}
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}

    # ── GET: health check ────────────────────────────────────────────────

    def do_GET(self):
        """Handle GET requests (health check, model list)."""
        parsed = urlparse(self.path)
        if parsed.path == "/v1/models":
            # Return available models (LU models + JARVIS meta info)
            try:
                # Try to connect to LU models
                import requests
                resp = requests.get(
                    f"{LU_API_BASE}/models",
                    headers={"Authorization": f"Bearer {os.environ.get('JARVIS_LLM_API_KEY', '')}"},
                    timeout=5,
                )
                if resp.status_code == 200:
                    models_data = resp.json()
                else:
                    models_data = {"data": []}
            except Exception:
                models_data = {"data": []}

            # Build response adding JARVIS marker
            result = {
                "object": "list",
                "data": models_data.get("data", []),
                "jarvis_meta": {
                    "agent_connected": agent is not None and agent._llm_connected
                    if agent else False,
                    "api_version": "v1",
                },
            }
            self._send_json(200, result)
        else:
            self._send_json(404, {"error": "Not found"})

    # ── POST: chat completions ─────────────────────────────────────────────

    def do_POST(self):
        """Handle POST /v1/chat/completions."""
        parsed = urlparse(self.path)

        # Only handle /v1/chat/completions
        if parsed.path != "/v1/chat/completions":
            self._send_json(404, {"error": "Not found"})
            return

        # Parse request body
        request_data = self._parse_json_body()

        if not request_data or "messages" not in request_data:
            self._send_json(400, {"error": "Invalid request: 'messages' required"})
            return

        # Extract the user's last user message
        messages = request_data.get("messages", [])
        user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break

        if not user_message.strip():
            self._send_json(400, {"error": "Empty user message"})
            return

        # ── Step 1: Run through the JARVIS agent ──────────────────────────
        # This gives us: loop cap, memory injection, tool execution, fact extraction
        agent_response = self._process_through_agent(user_message)

        # ── Step 2: Store interaction in memory ─────────────────────────────
        # (User + assistant messages, fact extraction)

        # ── Step 3: Return the response ───────────────────────────────────
        # Build the OpenAI-compatible response
        response = {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": llm.model if llm else "lu/D:\AI models\orcarouter_Qwen3.8-27B-Uncensored-IQ2_M.gguf",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": agent_response
                        if agent_response
                        else (user_message or "I'm not sure how to help with that."),
                    },
                    "finish_reason": "stop",
                }
            ],
            # Include Jarvis metadata for the UI to detect agent involvement
            "_jarvis_meta": {
                "agent_connected": agent is not None and agent._llm_connected
                if agent else False,
                "memory_count": self._get_memory_count(),
                "tool_iterations": getattr(agent, "last_tool_iterations", 0)
                if agent
                else 0,
            },
        }

        self._send_json(200, response)

    def _get_memory_count(self):
        """Get approximate memory count for metadata."""
        try:
            if retrieval:
                # Count via scored search with empty query
                results = retrieval.scored_search(
                    "", limit=1, candidates=1, db_path=MEMORY_DB
                )
                return len(results)
        except Exception:
            pass
        return 0

    # ── Internal: process user message through the agent ──────────────────

    def _process_through_agent(self, user_message):
        """Process a user message through the JARVIS agent loop.

        Returns the assistant's response string.
        """
        if not agent:
            # Fallback: direct LLM generate
            if llm:
                try:
                    return llm.generate(
                        system=SYSTEM_PROMPT,
                        user=user_message,
                        max_attempts=1,
                        timeout=60,
                    )
                except Exception:
                    return "I'm not sure how to help with that."
            return "I'm not sure how to help with that."

        # Build the memory-augmented system prompt
        system_prompt = SYSTEM_PROMPT
        try:
            # Add resume brief
            if agent.resume_brief:
                system_prompt = (
                    SYSTEM_PROMPT
                    + "\n## Resume Brief\n"
                    + agent.resume_brief
                )

            # Add relevant memories from scored retrieval
            try:
                relevant = retrieval.scored_search(
                    user_message, limit=5, candidates=20, db_path=MEMORY_DB
                )
                if relevant:
                    mem_lines = []
                    for m in relevant:
                        mem_lines.append(
                            f"- {m['text']} (importance={m['importance']}, confidence={m['confidence']:.2f})"
                        )
                    system_prompt = (
                        system_prompt
                        + "\n## Remembered Facts\n"
                        + "\n".join(mem_lines)
                    )
            except Exception:
                pass
        except Exception:
            pass

        # Run the agent's _llm_route method
        try:
            # For the first iteration, just route through LLM
            parsed = agent._llm_route(user_message, system_prompt=system_prompt)

            # If agent returns a direct answer (no tool), use it
            if parsed.get("tool") is None:
                answer = parsed.get("answer", "")
                # Store facts from this turn
                try:
                    extraction.extract_and_store(
                        user_text=user_message,
                        assistant_text=answer,
                        llm_fn=lambda p: llm.generate(
                            system=system_prompt, user=p,
                            max_attempts=1, timeout=60,
                        )
                        if llm
                        else None,
                        source_episode=getattr(agent, "session_id", "unknown")
                        if agent
                        else "unknown",
                        db_path=MEMORY_DB,
                    )
                except Exception as e:
                    # Log extraction error but don't block the response
                    print(f"[Jarvis API] Extraction warning: {e}")
                return answer

            # If agent calls a tool, execute it AND extract facts
            tool = parsed.get("tool")
            args = parsed.get("args", {})

            if tool and tool in agent.policy.get("allowed_tools", []):
                try:
                    result = agent._execute_tool(tool, {"tool": tool, "args": args})
                    # Store the tool interaction
                    try:
                        memory_mod.log_episode(
                            agent.session_id if agent else "unknown",
                            "assistant",
                            f"Tool: {tool}, Args: {str(args)[:200]}",
                            db_path=MEMORY_DB,
                        )
                    except Exception:
                        pass
                    # Extract facts from the tool result — this is the assistant's
                    # completed turn, so we should extract durable information
                    try:
                        extraction.extract_and_store(
                            user_text=user_message,
                            assistant_text=str(result)[:500],
                            llm_fn=lambda p: llm.generate(
                                system=system_prompt, user=p,
                                max_attempts=1, timeout=60,
                            )
                            if llm
                            else None,
                            source_episode=getattr(agent, "session_id", "unknown")
                            if agent
                            else "unknown",
                            db_path=MEMORY_DB,
                        )
                    except Exception as e:
                        # Log but don't block the response
                        print(f"[Jarvis API] Extraction warning after tool: {e}")
                    # Return the tool result as part of the response
                    return f"[Tool executed: {tool}] {str(result)[:200]}"
                except Exception as e:
                    # Store the failed tool attempt
                    try:
                        memory_mod.log_episode(
                            agent.session_id if agent else "unknown",
                            "assistant",
                            f"Tool failed: {tool} - {str(e)[:100]}",
                            db_path=MEMORY_DB,
                        )
                    except Exception:
                        pass
                    return f"Tool execution failed: {str(e)[:200]}"

            # If we get here, agent didn't give a clean answer;
            # fall back to a direct response
            # Extract facts from the completed assistant turn
            try:
                extraction.extract_and_store(
                    user_text=user_message,
                    assistant_text=str(result)[:500] if result else "",
                    llm_fn=lambda p: llm.generate(
                        system=system_prompt, user=p,
                        max_attempts=1, timeout=60,
                    )
                    if llm
                    else None,
                    source_episode=getattr(agent, "session_id", "unknown")
                    if agent
                    else "unknown",
                    db_path=MEMORY_DB,
                )
            except Exception as e:
                # Log but don't block the response
                print(f"[Jarvis API] Extraction warning direct: {e}")
            return "I'm processing your request. Please try again."

        except Exception as e:
            # Fallback on any error
            import traceback
            traceback.print_exc()
            return f"I encountered an error: {str(e)[:200]}"


def run_server(port=JARVIS_API_PORT):
    """Run the Jarvis API HTTP server."""
    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, JarvisAPIHandler)
    print(f"\n🚀 JARVIS API server starting at http://127.0.0.1:{port}/v1/")
    print("   Press Ctrl+C to stop the server.\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 JARVIS API server stopped.")
        httpd.server_close()


def main():
    """Entry point for the Jarvis API server."""
    print("=" * 50)
    print("  JARVIS API — Local OpenAI-compatible Chat Completion Server")
    print("=" * 50)
    print()

    # Initialize the JARVIS agent
    init_agent()

    # Start the HTTP server in a thread (so we can also run other things)
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 JARVIS API server stopped.")


if __name__ == "__main__":
    main()