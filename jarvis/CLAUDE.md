# JARVIS: rules for Claude Code

Goal, in priority order: (1) intelligence/reasoning quality, (2) speed, (3) context-token efficiency.
Speed and tokens must never cost reasoning quality. A change that lowers the eval score is reverted.

## Working rules
- Work ONLY on branch `self-improve`. Never touch main. Commit after each kept change.
- One small change per iteration. Run `python eval/run_eval.py` before and after.
- Keep a change only if the score improves or stays equal with no regressions. Otherwise `git revert`.
- Use dedicated tools (Read/Edit/Grep/Glob) for files. Shell only when nothing else covers it.
- Use absolute paths. Shell timeouts 60s or less. Don't retry the same command shape twice without saying what changed.
- State the goal in one sentence before running any command.
- Mark every number "measured" or "estimated". Never present a guess as a result.
- The eval is DRY-RUN: it must never execute tools, write files, or hit the network.

## Needs explicit human approval (stop and ask)
- Any edit to path guards, dangerous_patterns, shell_execute, or the confirmation logic
- Any edit to this file, .claude/settings.json, or the eval harness scoring
- Deleting files, installing packages, network calls, changing model/backend config

## Known issues (from review)
- Path guards: exact-match vs substring behavior is unclear. Correct fix is `Path.resolve()` then
  `is_relative_to(allowed_root)`; handles `..`, symlinks, and sibling folders like `JARVIS_evil`.
- shell_execute uses shell=True with a regex blocklist (bypassable). Prefer an allowlist + confirmation.
- web_fetch has no localhost/internal-URL (SSRF) guard.
- `_parse_request` uses substring matching ("read the readme" -> path "the readme").
- LocalLLM exists but is never called. No LLM backend was reachable at localhost:1234 or :11434.
- memories table has 0 rows, so token-efficiency work is premature.

## Plan order
1. Baseline eval (measured). 2. Fix path guards (with approval). 3. Get a model running; measure
tokens/sec, TTFT, context, VRAM (12 GB RTX 4070). 4. Wire LLM as bounded observe-act loop with
schema-constrained output, validate, one retry, fallback to strict keyword fast path.
5. Compare candidate models on the eval. 6. Only then trim context.
