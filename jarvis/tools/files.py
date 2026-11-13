"""Safe file operations wrapper."""
import os
import re
from typing import List, Optional
import json

# Import policy from parent package
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import load_policy


def file_read(path: str) -> str:
    """Read a file's contents."""
    policy = load_policy()
    allowed_paths = policy.get("allowed_paths", {}).get("read", [])
    if path not in allowed_paths and "D:\\AI models\\JARVIS" not in path:
        return f"Path not allowed for read: {path}"
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except FileNotFoundError:
        return f"File not found: {path}"
    except PermissionError:
        return f"Permission denied: {path}"
    except Exception as e:
        return f"Error: {e}"


def file_write(path: str, content: str) -> str:
    """Write content to a file."""
    policy = load_policy()
    allowed_paths = policy.get("allowed_paths", {}).get("write", [])
    if path not in allowed_paths and "D:\\AI models\\JARVIS" not in path:
        return f"Path not allowed for write: {path}"
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote {path}"
    except Exception as e:
        return f"Error: {e}"


def file_list(path: str, recursive: bool = False, pattern: Optional[str] = None) -> str:
    """List directory contents."""
    policy = load_policy()
    allowed_paths = policy.get("allowed_paths", {}).get("read", [])
    if path not in allowed_paths and "D:\\AI models\\JARVIS" not in path:
        return f"Path not allowed for list: {path}"
    try:
        if recursive:
            results = []
            for root, dirs, files in os.walk(path):
                for name in files:
                    results.append(f"{os.path.join(root, name)}")
            return "\n".join(results)
        else:
            entries = []
            for name in os.listdir(path):
                full_path = os.path.join(path, name)
                if os.path.isdir(full_path):
                    entries.append(f"[DIR] {name}")
                else:
                    entries.append(f"[FILE] {name}")
            return "\n".join(entries)
    except Exception as e:
        return f"Error: {e}"


def file_search(path: str, pattern: str, max_results: int = 50) -> str:
    """Search files recursively for a regex pattern."""
    policy = load_policy()
    allowed_paths = policy.get("allowed_paths", {}).get("read", [])
    if path not in allowed_paths and "D:\\AI models\\JARVIS" not in path:
        return f"Path not allowed for search: {path}"
    try:
        results = []
        for root, _, files in os.walk(path):
            for filename in files:
                filepath = os.path.join(root, filename)
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        for i, line in enumerate(f, 1):
                            if re.search(pattern, line):
                                results.append(f"{filepath}:{i}: {line.strip()}")
                                if len(results) >= max_results:
                                    break
                except Exception:
                    pass
        return "\n".join(results) if results else "No matches found."
    except Exception as e:
        return f"Error: {e}"