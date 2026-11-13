"""Extraction pipeline module — extracts factual memories from LLM responses."""

import json
import re
from typing import List, Optional, Any


def build_extraction_prompt(user_text: str, assistant_text: str) -> str:
    """Build the extraction prompt for the LLM.

    Given a user message and assistant response, produce a prompt that asks
    the LLM to extract factual candidates as JSON.

    Returns:
        A string prompt suitable for passing to the LLM's generate() method.
    """
    return f"""Extract factual memories from the following conversation turn.

User said: "{user_text}"
Assistant responded: "{assistant_text}"

Extract any factual information (project names, codenames, preferences, 
objectives, dates, locations, people, or other named facts) as a JSON array 
of candidate objects. Each candidate must have exactly three fields:

- "text": the factual statement (string)
- "type": a category label (string) — use: "project", "preference", "fact", 
  "person", "date", "location", or "other"
- "importance": an integer from 1 (trivial) to 10 (critical)

If no factual information should be extracted, return an empty JSON array "[]".

Important rules:
- Only extract information that is explicitly stated or can be reliably 
  inferred from the conversation.
- Do NOT include conversational filler, greetings, or general chit-chat.
- The JSON must be valid and parseable by json.loads().

Prompt:
"""


def parse_candidates(raw: str) -> List[dict]:
    """Parse JSON candidate objects from the LLM's raw response string.

    Returns a list of dicts, each with keys 'text', 'type', 'importance'.
    Returns an empty list if no valid candidates can be parsed.
    """
    if not raw or not raw.strip():
        return []

    # Strip common surrounding text and find the JSON array
    stripped = raw.strip()

    # Attempt to find a top-level JSON array [ ... ]
    match = re.search(r'^\s*\[.*\]\s*$', stripped, re.DOTALL)
    if match:
        try:
            candidates = json.loads(match.group(0))
            if isinstance(candidates, list):
                # Validate each candidate has the required fields
                valid = []
                for c in candidates:
                    if isinstance(c, dict) and "text" in c and "type" in c and "importance" in c:
                        valid.append({
                            "text": str(c["text"]),
                            "type": str(c["type"]),
                            "importance": int(c["importance"]),
                        })
                return valid
        except (json.JSONDecodeError, ValueError):
            pass

    # Try to find a JSON array embedded in text (e.g. after "Here are the "
    # candidates:" or similar)
    embedded_match = re.search(r'\[.*\]', stripped, re.DOTALL)
    if embedded_match:
        try:
            candidates = json.loads(embedded_match.group(0))
            if isinstance(candidates, list):
                valid = []
                for c in candidates:
                    if isinstance(c, dict) and "text" in c and "type" in c and "importance" in c:
                        valid.append({
                            "text": str(c["text"]),
                            "type": str(c["type"]),
                            "importance": int(c["importance"]),
                        })
                return valid
        except (json.JSONDecodeError, ValueError):
            pass

    return []