"""Safe shell execution wrapper."""
import subprocess
import re
import os
from typing import Optional
import json

# Import policy from parent package
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import load_policy

DANGEROUS_PATTERNS = [
    r"rm\s+-rf",
    r"del\s+/f\s+/s\s+/q",
    r"format\s+",
    r"sudo\s+-i",
    r"certutil\s+decode",
    r"powershell\s+-enc",
    r"eval\s*\(",
]


def validate_command(command: str) -> Optional[str]:
    """Validate a command against dangerous patterns. Returns error message or None."""
    policy = load_policy()
    for pattern in policy.get("dangerous_patterns", []):
        if re.search(pattern, command, re.IGNORECASE):
            return f"Command blocked: matches dangerous pattern '{pattern}'"
    return None


def shell_read(path: str, limit: int = 100) -> str:
    """Read a file using subprocess (echo | Out-File)."""
    policy = load_policy()
    allowed_paths = policy.get("allowed_paths", {}).get("read", [])
    if path not in allowed_paths and "D:\\AI models\\JARVIS" not in path:
        return f"Path not allowed for read: {path}"
    try:
        result = subprocess.run(
            ["powershell", "-Command", f"Get-Content -Path '{path}' -TotalCount {limit}"],
            capture_output=True, text=True, timeout=120
        )
        return result.stdout if result.stdout else result.stderr
    except subprocess.TimeoutExpired:
        return "Command timed out"
    except Exception as e:
        return f"Error: {e}"


def shell_execute(command: str, timeout: int = 60) -> str:
    """Execute a shell command safely. Returns stdout + stderr."""
    policy = load_policy()
    error = validate_command(command)
    if error:
        return f"BLOCKED: {error}"

    if timeout > policy.get("limits", {}).get("timeout", 120):
        timeout = policy.get("limits", {}).get("timeout", 120)

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={
                k: v for k, v in os.environ.items()
                if k not in ("PATH", "PYTHONPATH", "TEMP")
            }
        )
        output = result.stdout + "\n" + result.stderr
        return output if output else "Command completed with no output"
    except subprocess.TimeoutExpired:
        return "Command timed out after " + str(timeout) + " seconds"
    except Exception as e:
        return f"Error: {e}"