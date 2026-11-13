"""extraction.py - Phase 2: fact extraction pipeline with injected LLM.

The language model is passed in as a function llm_fn(prompt) -> str.
Never calls a real model. Standard library only.
"""

import json
import re
import time

import memory


def build_extraction_prompt(user_text, assistant_text):
    """Build the prompt sent to the LLM for fact extraction."""
    return (
        "You are a memory extraction engine. Extract durable facts from the "
        "conversation below.\n"
        "\n"
        "Return ONLY a JSON list of at most 3 objects with these keys:\n"
        '  {"text": <short single fact>, "type": <one of fact/preference/project/correction>, '
        '"importance": <integer 1-10>}\n'
        "\n"
        "Return [] when nothing is worth remembering long-term.\n"
        "\n"
        "Be stingy: skip small talk, one-off requests and anything not durable.\n"
        "\n"
        "Conversation:\n"
        f"User: {user_text}\n"
        f"Assistant: {assistant_text}\n"
    )


def parse_candidates(raw):
    """Parse raw LLM output into a list of valid candidate dicts.

    Strips markdown code fences, takes the text from the first "[" to the
    last "]", parses JSON. Keeps only items with a non-empty string "text"
    (max 200 chars), a valid type, and an integer importance (clamped to
    1-10). Max 3 items. Never raises: any bad input returns [].
    """
    if not isinstance(raw, str):
        return []
    # Strip markdown code fences.
    text = raw.strip()
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    # Take from first "[" to last "]".
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end < start:
        return []
    text = text[start:end + 1]
    try:
        data = json.loads(text)
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    valid_types = {"fact", "preference", "project", "correction"}
    result = []
    for item in data:
        if not isinstance(item, dict):
            continue
        t = item.get("text")
        if not isinstance(t, str) or not t:
            continue
        if len(t) > 200:
            continue
        typ = item.get("type")
        if isinstance(typ, str):
            typ = typ.lower()
        if typ not in valid_types:
            continue
        imp = item.get("importance")
        if isinstance(imp, bool):
            continue
        if isinstance(imp, int):
            imp = int(imp)
        elif isinstance(imp, float) and imp.is_integer():
            imp = int(imp)
        elif isinstance(imp, str):
            try:
                imp = int(imp)
            except ValueError:
                continue
        else:
            continue
        imp = max(1, min(10, imp))
        result.append({"text": t, "type": typ, "importance": imp})
        if len(result) == 3:
            break
    return result


def process_candidate(cand, source_episode=None, db_path=None):
    """Process one candidate: insert or mark as duplicate.

    Returns {"action": "inserted"|"duplicate", "id": int}.
    """
    # Search for potential duplicates.
    hits = memory.search_keyword(cand["text"], limit=8, db_path=db_path)
    now = time.time()
    words = set(re.findall(r"\w+", cand["text"].lower()))
    for hit in hits:
        hit_words = set(re.findall(r"\w+", hit["text"].lower()))
        if not hit_words and not words:
            jaccard = 1.0
        else:
            union = len(hit_words | words)
            jaccard = len(hit_words & words) / union if union else 0.0
        if jaccard >= 0.8:
            # Duplicate: raise confidence, set last_used, increment use_count.
            new_conf = min(1.0, hit["confidence"] + 0.1)
            with memory._connect(db_path) as conn:
                conn.execute(
                    "UPDATE memories SET confidence = ?, last_used = ?, "
                    "use_count = use_count + 1 WHERE id = ?",
                    (new_conf, now, hit["id"]))
            return {"action": "duplicate", "id": hit["id"]}
    # No duplicate: insert new.
    new_id = memory.add_memory(cand["text"], type=cand["type"],
                                importance=cand["importance"],
                                source_episode=source_episode,
                                confidence=0.5, db_path=db_path)
    return {"action": "inserted", "id": new_id}


def supersede(old_id, new_id, db_path=None):
    """Set superseded_by on the old memory to new_id.

    Raises ValueError if either id does not exist.
    """
    if old_id == new_id:
        raise ValueError("old_id and new_id must be different")
    with memory._connect(db_path) as conn:
        for mid in (old_id, new_id):
            row = conn.execute("SELECT id FROM memories WHERE id = ?",
                                (mid,)).fetchone()
            if row is None:
                raise ValueError(f"memory id {mid} does not exist")
        conn.execute(
            "UPDATE memories SET superseded_by = ? WHERE id = ?",
            (new_id, old_id))


def extract_and_store(user_text, assistant_text, llm_fn,
                      source_episode=None, db_path=None):
    """Full pipeline: build prompt, call LLM, parse, process candidates.

    Never raises. If llm_fn fails, returns [].
    """
    prompt = build_extraction_prompt(user_text, assistant_text)
    try:
        raw = llm_fn(prompt)
    except Exception:
        return []
    candidates = parse_candidates(raw)
    results = []
    for cand in candidates:
        try:
            results.append(process_candidate(cand, source_episode=source_episode,
                                              db_path=db_path))
        except Exception:
            continue
    return results
