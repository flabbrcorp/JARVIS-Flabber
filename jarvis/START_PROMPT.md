Read CLAUDE.md first and follow it strictly. Do not modify any file yet.

Step 1, read-only: read agent.py, Jarvis.py, and the tool implementations. Show me the exact code of
_parse_request, handle_request, every path guard, and where LocalLLM is defined and called.

Step 2: adapt eval/run_eval.py's route() so it calls the real router in DRY-RUN mode (no tool execution).
Show me the diff and wait for my approval, since this is the scoring harness.

Step 3: after approval, run `python eval/run_eval.py`, report the MEASURED baseline, and commit it on
branch self-improve.

Step 4: propose (don't apply) the path-guard fix using Path.resolve() + is_relative_to, with tests for
"..", symlinks, and sibling folders like JARVIS_evil. Wait for my approval.

Then stop and summarize. Mark every number measured or estimated.
