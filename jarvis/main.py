"""JARVIS Core - Main Entry Point."""
import os
import json
import sys
from datetime import datetime
from pathlib import Path

# Set encoding for console output
sys.stdout.reconfigure(encoding='utf-8')

from agent import Agent, DEFAULT_POLICY
from config import load_config, load_policy, save_config


def main():
    """Main entry point for JARVIS Core."""
    # Load or set default policy
    if not os.path.exists("config/policy.json"):
        save_config({"policy_path": "config/policy.json"})
        print("\n[!] No policy found. Using defaults.")
        print("    Set your own policy with: set_policy: <path-to-policy.json>")
        print()

    # Load state
    state_path = Path("state") / "current_task.json"
    if state_path.exists():
        with open(state_path) as f:
            state = json.load(f)
    else:
        state = {"status": "idle", "task": "", "created_at": datetime.now().isoformat()}

    # Initialize agent
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
    print("    set_policy: <path>      — set policy from file")
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