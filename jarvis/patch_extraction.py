#!/usr/bin/env python
"""Patch jarvis_api.py to add extraction after direct-answer fallback."""
import re

with open(r"D:\AI models\jarvis\jarvis_api.py", "r", encoding="utf-8") as f:
    content = f.read()

old_text = """# If we get here, agent didn't give a clean answer;
            # fall back to a direct response
            return "I'm processing your request. Please try again.""""

new_text = """# If we get here, agent didn't give a clean answer;
            # fall back to a direct response
            # Extract facts from the completed assistant turn
            try:
                extraction.extract_and_store(
                    user_text=user_message,
                    assistant_text=str(result)[:500] if result else "",
                    llm_fn=lambda p: llm.generate(
                        system=system_prompt, user=p,
                        max_attempts=1, timeout=60,
                    )
                    if llm
                    else None,
                    source_episode=getattr(agent, "session_id", "unknown")
                    if agent
                    else "unknown",
                    db_path=MEMORY_DB,
                )
            except Exception as e:
                # Log but don't block the response
                print(f"[Jarvis API] Extraction warning direct: {e}")
            return "I'm processing your request. Please try again.""""

if old_text in content:
    new_content = content.replace(old_text, new_text)
    with open(r"D:\AI models\jarvis\jarvis_api.py", "w", encoding="utf-8") as f:
        f.write(new_content)
    print("PATCH APPLIED SUCCESSFULLY")
else:
    print("OLD TEXT NOT FOUND - content sample:")
    # Show lines around the target
    lines = content.split("\n")
    for i, line in enumerate(lines[335:345], start=336):
        print(f"{i}: {line}")