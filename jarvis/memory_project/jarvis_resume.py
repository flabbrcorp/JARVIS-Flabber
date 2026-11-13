"""Jarvis resume/task tracking module — minimal implementation."""

import json
import os
from datetime import datetime
from typing import Optional, Dict, Any


def _ensure_state_dir(state_dir: str = None) -> str:
    """Ensure the state directory exists, return its path."""
    if state_dir is None:
        state_dir = os.environ.get("JARVIS_STATE_DIR", "state")
    os.makedirs(state_dir, exist_ok=True)
    return state_dir


def _log_path(state_dir: str = None, filename: str = "current_task.json") -> str:
    """Return the full path to a state log file."""
    return os.path.join(_ensure_state_dir(state_dir), filename)


def _write_json(path: str, data: Dict[str, Any]) -> None:
    """Write a JSON object to a file, creating directories as needed."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _append_objective_log(objective: str, status: str,
                         state_dir: str = None, filename: str = "objective_log.jsonl") -> None:
    """Append an objective status entry to a log file."""
    log_path = os.path.join(_ensure_state_dir(state_dir), filename)
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "objective": objective,
        "status": status,
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


# Public API

def save_current_task(task: dict, state_dir: str = None) -> None:
    """Save the current task state to a JSON file."""
    path = _log_path(state_dir, "current_task.json")
    _write_json(path, task)


def set_task(objective: str, state_dir: str = None) -> str:
    """Set a new active task and log the update."""
    state_dir = _ensure_state_dir(state_dir)
    task = {
        "objective": objective,
        "steps_completed": [],
        "current_step": None,
        "updated_at": datetime.now().isoformat(),
    }
    save_current_task(task, state_dir=state_dir)
    _append_objective_log(objective, "active", state_dir=state_dir)
    return f"✅ Task set: '{objective}'"


def get_current_task(state_dir: str = None) -> Optional[dict]:
    """Get the current active task from the state file."""
    path = _log_path(state_dir, "current_task.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError):
        return None


def update_step(description: str, state_dir: str = None) -> str:
    """Mark a step as completed in the current task."""
    task = get_current_task(state_dir=state_dir)
    if not task:
        return "No active task set. Use 'set_task: <objective>' first."
    if task.get("current_step") != description:
        task["steps_completed"].append(description)
    task["current_step"] = description
    task["updated_at"] = datetime.now().isoformat()
    save_current_task(task, state_dir=state_dir)
    return f"✅ Step completed: {description}"


def reset_task(state_dir: str = None) -> str:
    """Reset the current task state."""
    path = _log_path(state_dir, "current_task.json")
    if os.path.exists(path):
        os.remove(path)
    return "✅ Task reset."