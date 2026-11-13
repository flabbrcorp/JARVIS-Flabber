"""retrieval.py - Phase 2: scored retrieval over memory.py.

Ranks memory.search_keyword candidates by a blend of relevance, recency,
importance and confidence. Standard library only.
"""

import time

import memory


def scored_search(query, limit=5, candidates=30, half_life_days=30, now=None,
                  db_path=None):
    """Scored search: candidates from memory.search_keyword, re-ranked as

    score = relevance x recency x (importance/10) x confidence

    relevance = row["score"] / max score among candidates (0..1);
    recency = 0.5 ** (age_days / half_life_days), age measured from
    last_used if set, otherwise created. `now` defaults to time.time().
    Returns the top `limit` rows as dicts plus "final_score", best first.
    """
    rows = memory.search_keyword(query, limit=candidates, db_path=db_path)
    if not rows:
        return []
    now = time.time() if now is None else now
    max_score = max(r["score"] for r in rows)
    for r in rows:
        r["relevance"] = r["score"] / max_score
        age_days = max(0.0, (now - (r["last_used"] or r["created"]))
                       / (24 * 3600))
        r["recency"] = 0.5 ** (age_days / half_life_days)
        r["final_score"] = (r["relevance"] * r["recency"]
                            * (r["importance"] / 10.0) * r["confidence"])
    rows.sort(key=lambda r: r["final_score"], reverse=True)
    return rows[:limit]


def bump_use(memory_ids, db_path=None):
    """For each id, set last_used to now and increment use_count.

    Unknown ids are ignored. Returns the number of rows actually bumped.
    """
    now = time.time()
    bumped = 0
    with memory._connect(db_path) as conn:
        for mid in memory_ids:
            cur = conn.execute(
                "UPDATE memories SET last_used = ?, use_count = use_count + 1 "
                "WHERE id = ?", (now, mid))
            bumped += cur.rowcount
    return bumped
