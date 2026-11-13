"""
DRY-RUN routing eval for JARVIS. Never executes tools, writes files, or touches the network.

FIRST RUN: the adapter in route() is a guess; I had not seen agent.py. Claude Code should open
agent.py, adapt route() to call the real router WITHOUT executing the tool, and report the change.
Special expected values: NONE_OR_LLM, MULTI_STEP, MEMORY_LOOKUP count as pass only if the router
does not confidently pick a wrong file/shell tool (baseline keyword router will usually fail them).
"""
import json, sys, time, pathlib, datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
SPECIAL = {"NONE_OR_LLM", "MULTI_STEP", "MEMORY_LOOKUP"}

def route(text):
    """Return (tool_name or None, args_string). MUST NOT execute the tool."""
    import agent  # adapt as needed
    A = getattr(agent, "Agent", None) or getattr(agent, "JarvisAgent", None)
    if A is None:
        raise RuntimeError("Adapt route(): no Agent class found in agent.py")
    try:
        inst = A()
    except TypeError:
        inst = A.__new__(A)
    out = inst._parse_request(text)
    # Normalize common shapes: (tool, args) | {"tool":..,"args":..} | None
    if out is None:
        return None, ""
    if isinstance(out, dict):
        return out.get("tool"), json.dumps(out.get("args", ""), ensure_ascii=False)
    if isinstance(out, (tuple, list)) and out:
        return out[0], json.dumps(out[1] if len(out) > 1 else "", ensure_ascii=False)
    return str(out), ""

def judge(case, tool, args):
    exp = case["tool"]
    if exp in SPECIAL:
        return tool in (None, "none", "llm")
    if tool != exp:
        return False
    a = args.lower()
    if any(s.lower() not in a for s in case.get("args_contain", [])):
        return False
    bad = case.get("args_must_not_equal", [])
    return not any(a.strip('"[]{} ').endswith(b.lower() + '"') or a.strip('"') == b.lower() for b in bad)

def main():
    cases = json.loads((pathlib.Path(__file__).parent / "eval_set.json").read_text(encoding="utf-8"))
    rows, t0 = [], time.perf_counter()
    for c in cases:
        try:
            tool, args = route(c["text"])
            ok, err = judge(c, tool, args), ""
        except Exception as e:
            tool, args, ok, err = None, "", False, f"{type(e).__name__}: {e}"
        rows.append({"id": c["id"], "cat": c["cat"], "ok": ok, "got": tool, "want": c["tool"], "args": args, "err": err})
        print(f'{"PASS" if ok else "FAIL"} #{c["id"]:>2} [{c["cat"]}] want={c["tool"]} got={tool} {err}')
    passed = sum(r["ok"] for r in rows)
    print(f"\nSCORE {passed}/{len(rows)}  (measured, dry-run, {time.perf_counter()-t0:.2f}s)")
    for cat in ("unambiguous", "ambiguous", "edge"):
        sub = [r for r in rows if r["cat"] == cat]
        print(f"  {cat}: {sum(r['ok'] for r in sub)}/{len(sub)}")
    out = pathlib.Path(__file__).parent / "results"
    out.mkdir(exist_ok=True)
    (out / f"{datetime.datetime.now():%Y%m%d_%H%M%S}.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")

if __name__ == "__main__":
    main()
