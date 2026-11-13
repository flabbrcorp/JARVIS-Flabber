"""JARVIS Tools — safe wrappers for agent tool calls."""
from .shell import shell_read, shell_execute
from .files import file_read, file_write, file_list, file_search
from .web import web_search, web_fetch

__all__ = [
    "shell_read", "shell_execute",
    "file_read", "file_write", "file_list", "file_search",
    "web_search", "web_fetch",
]