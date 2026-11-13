"""Configuration management."""
import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config", "config.json")
POLICY_PATH = os.path.join(os.path.dirname(__file__), "config", "policy.json")


def load_config() -> dict:
    """Load configuration from file."""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return {
        "tavily_api_key": "",
        "default_timeout": 60,
        "max_file_size_kb": 102400,
    }


def save_config(config: dict = None):
    """Save configuration to file."""
    if config is None:
        config = load_config()
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def load_policy() -> dict:
    """Load the policy from the policy.json file."""
    if os.path.exists(POLICY_PATH):
        with open(POLICY_PATH, "r") as f:
            return json.load(f)
    return {
        "version": "1.0",
        "dangerous_patterns": ["rm -rf", "del /f /s /q", "format", "sudo -i"],
        "allowed_paths": {
            "read": ["C:\\Users\\{USER}\\Desktop", "C:\\Users\\{USER}\\Documents", "D:\\AI models\\JARVIS"],
            "write": ["C:\\Users\\{USER}\\Documents\\JARVIS_LOGS"],
            "execute": ["C:\\Python39\\python.exe"],
        },
        "limits": {"timeout": 120, "max_processes": 10},
        "allowed_tools": ["shell_read", "shell_execute", "file_read", "file_write", "file_list", "file_search", "web_search", "web_fetch"],
    }


def set_policy(policy: dict):
    """Save a policy to the policy.json file."""
    os.makedirs(os.path.dirname(POLICY_PATH), exist_ok=True)
    with open(POLICY_PATH, "w") as f:
        json.dump(policy, f, indent=2)


def set_policy_file(path: str):
    """Set the policy path for the config."""
    config = load_config()
    config["policy_path"] = path
    save_config(config)


def get_policy() -> dict:
    """Get the policy from the config file."""
    config = load_config()
    policy_path = config.get("policy_path", POLICY_PATH)
    if os.path.exists(policy_path):
        with open(policy_path, "r") as f:
            return json.load(f)
    return load_policy()