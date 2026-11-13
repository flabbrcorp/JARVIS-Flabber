# JARVIS Memory — Overnight Build Log

Started: 2026-10-28. Working rules: one task at a time, tests run with
`python test_<name>.py`, temp DBs only, stdlib only.

## Final summary

### Task A — retrieval.py (scored search)
Status: DONE
Files created: retrieval.py, test_retrieval.py
Test output: `All 10 checks passed.`

### Task B — core_memory.py (small always-in-prompt tier)
Status: DONE
Files created: core_memory.py, test_core_memory.py
Test output: `All 12 checks passed.`

### Task C — extraction.py (fact extraction pipeline)
Status: DONE
Files created: extraction.py, test_extraction.py
Test output: `All 31 checks passed.`

### Existing modules (untouched, re-verified)
test_memory.py still passes: `All 22 checks passed.`

## Fix pass changes
1. extraction.py extract_and_store: wrapped each process_candidate call in try/except Exception; failures are skipped so the function truly never raises.
2. extraction.py parse_candidates: caught Exception (not only JSONDecodeError) around json.loads.
3. extraction.py parse_candidates: importance accepts int, float (is_integer), numeric string; rejects bools and non-numeric strings. Type is lowercased before validation.
4. extraction.py process_candidate: Jaccard computed on re.findall(r"\w+", text.lower()) so punctuation doesn't matter.
5. extraction.py supersede: raises ValueError if old_id == new_id.
6. extraction.py: removed unused `import retrieval`. core_memory.py: set_core docstring fixed (returns update timestamp, not row id); whitespace-only keys or values rejected with ValueError.

## Decisions
- retrieval.py: `now=None` defaults to time.time(); recency age clamped
  to >= 0 (future timestamps don't produce >1 recency). scored_search
  mutates the candidate dicts (adds relevance, recency, final_score) —
  acceptable since they are fresh dicts from search_keyword each call.
- test_retrieval.py: deterministic-clock check uses >= on scores because
  two identical rows at the same injected clock produce identical floats.
  All tests pin created/last_used to an injected NOW constant rather than
  relying on wall-clock, so results are reproducible.
- core_memory.py: set_core uses ON CONFLICT(key) DO UPDATE for
  insert-or-replace; CoreMemoryFull is raised before any write so data
  stays unchanged. Whitespace-only keys/values rejected via .strip() check.
- extraction.py: parse_candidates strips markdown fences, takes first [
  to last ], parses JSON with Exception catch. process_candidate uses
  word-set Jaccard >= 0.8 (re.findall r"\w+") for duplicate detection.
  supersede raises ValueError on missing ids or old_id == new_id.
  extract_and_store wraps llm_fn in try/except and each process_candidate
  in try/except.

## Blocked
(none)
