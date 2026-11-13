#!/usr/bin/env python
"""Fix agent.py: move extract_and_store out of error handler."""
import re

with open(r"D:\AI models\jarvis\agent.py", "r", encoding="utf-8") as f:
    content = f.read()

# The current pattern: extraction inside error handler
old_pattern = """# If extraction has not been performed yet and this was a completed assistant turn:
            try:
                extraction.extract_and_store(user_text, assistant_text, llm_fn, source_episode, db_path)
except Exception as e:
                # Log extraction errors but don't block the response
                print(f"[Agent] Extraction warning: {e}")"""

# The new pattern: extraction after logging, independent
new_pattern = """# Log episode outcome (independent of memory extraction)
            try:
                memory_mod.log_episode(self.session_id, "assistant", response, db_path=MEMORY_DB)
            except Exception as e:
                # Log but don't block - extraction runs regardless
                print(f"[Agent] Episode logging warning: {e}")

            # Extract facts from the completed assistant turn (runs once per turn)
            try:
                extraction.extract_and_store(
                    user_text=user_text,
                    assistant_text=assistant_text,
                    llm_fn=llm_fn,
                    source_episode=source_episode,
                    db_path=MEMORY_DB,
                )
            except Exception as e:
                # Log extraction errors but don't interrupt user's response
                print(f"[Agent] Extraction warning: {e}")

            return response"""

if old_pattern in content:
    new_content = content.replace(old_pattern, new_pattern)
    with open(r"D:\AI models\jarvis\agent.py", "w", encoding="utf-8") as f:
        f.write(new_content)
    print("FIX APPLIED SUCCESSFULLY")
else:
    print("OLD PATTERN NOT FOUND")
    # Show what's around the target area
    lines = content.split("\n")
    for i, line in enumerate(lines, 1):
        if 'extract_and_store' in line:
            print(f"Line {i}: {line.rstrip()}")
            # Show context
            for j in range(max(0, i-3), min(len(lines), i+3)):
                print(f"  {j+1}: {lines[j].rstrip()}")