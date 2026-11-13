"""Web access wrapper."""
import re
import json
import urllib.request
import urllib.error
import urllib.parse
from typing import Optional
import os
import sys

# Import policy from parent package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import load_policy


def web_search(query: str, max_results: int = 5) -> str:
    """Perform a web search. Returns ranked results."""
    policy = load_policy()
    try:
        encoded_query = urllib.parse.quote(query)
        api_key = policy.get("tavily_api_key", "")
        url = f"https://api.tavily.com/search?q={encoded_query}&api_key={api_key}&max_results={max_results}"
        headers = {"Accept": "application/json"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
        results = "\n".join(
            f"[{i+1}] {r['title']}\n    {r['url']}\n    {r['snippet']}"
            for i, r in enumerate(data.get("results", []))
        )
        return results if results else "No results found."
    except urllib.error.HTTPError as e:
        return f"HTTP error: {e.code} {e.reason}"
    except urllib.error.URLError as e:
        return f"Network error: {e.reason}"
    except Exception as e:
        return f"Error: {e}"


def web_fetch(url: str, max_length: int = 24000) -> str:
    """Fetch and return the readable text content of a URL."""
    policy = load_policy()
    if "://" not in url:
        return "URL must include protocol (http:// or https://)"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "JARVIS/1.0"})
        with urllib.request.urlopen(req, timeout=60) as response:
            content = response.read().decode("utf-8", errors="replace")
            return content[:max_length]
    except urllib.error.HTTPError as e:
        return f"HTTP error: {e.code} {e.reason}"
    except urllib.error.URLError as e:
        return f"Network error: {e.reason}"
    except Exception as e:
        return f"Error: {e}"