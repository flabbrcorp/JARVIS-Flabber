#!/usr/bin/env python
import sys
sys.path.insert(0, r"D:\AI models\jarvis")

# Read the file
with open(r"D:\AI models\jarvis\jarvis_api.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix 1: Tool branch - change source_episode
old_tool = "source_episode=getattr(agent, \"session_id\", \"unknown\") if agent else \"unknown\""
new_tool = "source_episode=None"

# Fix 2: Direct-answer branch extraction
old_direct = """source_episode=getattr(agent, \"session_id\", \"unknown\") if agent else \"unknown\""""
new_direct = """source_episode=None"""

modified = False

if old_tool in content:
    content = content.replace(old_tool, new_tool)
    print("Fix 1 (tool branch) APPLIED")
    modified = True
else:
    print("Fix 1: old text not found for tool branch")

if old_direct in content:
    content = content.replace(old_direct, new_direct)
    print("Fix 2 (direct-answer branch) APPLIED")
    modified = True
else:
    print("Fix 2: old text not found for direct-answer branch")

if modified:
    with open(r"D:\AI models\jarvis\jarvis_api.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("PATCH APPLIED SUCCESSFULLY")
else:
    print("OLD TEXTS NOT FOUND - some changes not applied")