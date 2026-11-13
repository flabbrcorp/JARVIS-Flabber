#!/usr/bin/env python
"""Patch jarvis_api.py to fix source_episode in extraction calls."""
import re

with open(r"D:\AI models\jarvis\jarvis_api.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix 1: Tool branch extraction - change source_episode
old_tool = """source_episode=getattr(agent, \"session_id\", \"unknown\") if agent else \"unknown\""""
new_tool = """source_episode=None"""

if old_tool in content:
    content = content.replace(old_tool, new_tool)
    print("Fix 1 (tool branch) APPLIED")
else:
    print("Fix 1: old text not found")

# Fix 2: Direct-answer branch extraction
old_direct = """source_episode=getattr(agent, \"session_id\", \"unknown\") if agent else \"unknown\""""
new_direct = """source_episode=None"""

if old_direct in content:
    content = content.replace(old_direct, new_direct)
    print("Fix 2 (direct-answer branch) APPLIED")
else:
    print("Fix 2: old text not found")

if old_tool in content or old_direct in content:
    with open(r"D:\AI models\jarvis\jarvis_api.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("PATCH APPLIED SUCCESSFULLY")
else:
    print("OLD TEXT NOT FOUND - some fixes may not have been applied")