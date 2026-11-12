#!/usr/bin/env python3
"""StackSense command-line interface.

  python stacksense.py run <scenario.json> [-o out.json] [--lenient] [--no-trace]
  python stacksense.py batch <scenarios.json|dir> [-d outputs/]   # one <ID>_output.json per scenario
  python stacksense.py validate <scenario.json>
  python stacksense.py describe "free-text project description"
  python stacksense.py kb [--export kb.json]
  python stacksense.py serve [--port 8000]

No third-party packages. LLM features are OFF unless STACKSENSE_LLM=on (they never affect the stack).
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from stacksense_engine.recommend import recommend, to_json  # noqa: E402
from stacksense_engine.validate import validate  # noqa: E402
from stacksense_engine.describe import parse_description  # noqa: E402
from stacksense_engine import kb  # noqa: E402

try:  # Windows consoles default to cp1252
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # pragma: no cover
    pass

SEV_ICON = {"critical": "[CRITICAL]", "warning": "[WARNING] ", "info": "[info]    "}


def _load(path):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        return {"__parse_error__": f"invalid JSON at line {e.lineno} column {e.colno}: {e.msg}"}


def _result_for(raw, args):
    if isinstance(raw, dict) and "__parse_error__" in raw:
        return {"scenario_id": None, "status": "invalid_input", "summary": "File is not valid JSON.",
                "architecture_style": "other", "stack": None,
                "estimated_monthly_cost_usd": {"min": 0, "max": 0, "assumptions": ["Not estimated"]},
                "warnings": [], "assumptions": [],
                "validation_errors": [{"field": "$", "message": raw["__parse_error__"]}]}
    return recommend(raw, lenient=args.lenient, include_trace=not args.no_trace)


def _print_human(r):
    print(f"\n=== {r.get('scenario_id') or '(no id)'}  status: {r['status']}  architecture: {r['architecture_style']}")
    print(r["summary"])
    if r.get("stack"):
        for k in ("frontend", "backend", "database", "hosting"):
            print(f"  {k:<10} {r['stack'][k]['choice']}")
        for s in r["stack"]["supporting"]:
            tag = s["layer"] + (f" ({s['purpose']})" if s.get("purpose") else "")
            print(f"  + {tag:<44} {s['choice']}")
    c = r["estimated_monthly_cost_usd"]
    print(f"  cost       ${c['min']:,} - ${c['max']:,} per month")
    for w in r.get("warnings", []):
        print(f"  {SEV_ICON[w['severity']]} {w['code']}: {w['message']}")
    for e in r.get("validation_errors", []):
        print(f"  [ERROR] {e['field']}: {e['message']}")


def cmd_run(args):
    raw = _load(args.file)
    r = _result_for(raw, args)
    out = args.output
    if out is None:
        sid = r.get("scenario_id") or os.path.splitext(os.path.basename(args.file))[0]
        out = os.path.join(HERE, "outputs", f"{sid}_output.json")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(to_json(r) + "\n")
    if not args.quiet:
        _print_human(r)
        print(f"\n  JSON written to {os.path.relpath(out)}")
    return 0 if r["status"] != "invalid_input" else 2


def cmd_batch(args):
    src = args.source
    scenarios = []
    if os.path.isdir(src):
        for name in sorted(os.listdir(src)):
            if name.endswith(".json"):
                raw = _load(os.path.join(src, name))
                if isinstance(raw, list):
                    scenarios.extend(raw)
                else:
                    if isinstance(raw, dict) and "scenario_id" not in raw:
                        raw = {**raw, "scenario_id": os.path.splitext(name)[0]}
                    scenarios.append(raw)
    else:
        raw = _load(src)
        scenarios = raw if isinstance(raw, list) else [raw]
    os.makedirs(args.dir, exist_ok=True)
    seen = set()
    for i, s in enumerate(scenarios):
        r = _result_for(s, args)
        sid = r.get("scenario_id") or f"scenario_{i + 1}"
        if sid in seen:
            continue
        seen.add(sid)
        path = os.path.join(args.dir, f"{sid}_output.json")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(to_json(r) + "\n")
        if not args.quiet:
            _print_human(r)
            print(f"  -> {path}")
    print(f"\n{len(seen)} result file(s) written to {args.dir}")
    return 0


def cmd_validate(args):
    raw = _load(args.file)
    if "__parse_error__" in raw:
        print(raw["__parse_error__"])
        return 2
    v = validate(raw, lenient=args.lenient)
    print(json.dumps({"valid": not v["errors"], "validation_errors": v["errors"], "assumptions": v["assumptions"],
                      "notes": v["notes"], "unknown_fields": v["unknown_fields"]}, indent=2))
    return 0 if not v["errors"] else 2


def cmd_describe(args):
    print(json.dumps(parse_description(args.text), indent=2))
    return 0


def cmd_kb(args):
    problems = kb.validate_kb()
    print(json.dumps(kb.stats(), indent=2))
    print("integrity:", "OK" if not problems else problems)
    if args.export:
        with open(args.export, "w", encoding="utf-8") as f:
            json.dump(kb.export(), f, indent=2, default=list)
        print("exported to", args.export)
    return 0 if not problems else 1


def cmd_serve(args):
    from stacksense_engine.server import serve
    serve(args.host, args.port)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="stacksense", description="StackSense tech-stack recommendation engine")
    ap.add_argument("--no-llm", action="store_true", help="force all LLM features off (they are off by default)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("run", "batch"):
        p = sub.add_parser(name)
        if name == "run":
            p.add_argument("file")
            p.add_argument("-o", "--output")
        else:
            p.add_argument("source", help="JSON file (object or array) or a directory of JSON files")
            p.add_argument("-d", "--dir", default=os.path.join(HERE, "outputs"))
        p.add_argument("--lenient", action="store_true", help="fill missing required fields with documented defaults")
        p.add_argument("--no-trace", action="store_true", help="omit decision_trace from the output")
        p.add_argument("-q", "--quiet", action="store_true")
    p = sub.add_parser("validate")
    p.add_argument("file")
    p.add_argument("--lenient", action="store_true")
    p = sub.add_parser("describe")
    p.add_argument("text")
    p = sub.add_parser("kb")
    p.add_argument("--export")
    p = sub.add_parser("serve")
    p.add_argument("--port", type=int, default=int(os.environ.get("STACKSENSE_PORT", "8000")))
    p.add_argument("--host", default=os.environ.get("STACKSENSE_HOST", "127.0.0.1"))
    args = ap.parse_args(argv)
    if args.no_llm:
        os.environ["STACKSENSE_LLM"] = "off"
    return {"run": cmd_run, "batch": cmd_batch, "validate": cmd_validate, "describe": cmd_describe,
            "kb": cmd_kb, "serve": cmd_serve}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
