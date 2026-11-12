"""Local-change analysis: perturb one input at a time on the public scenarios and count how many
core decisions (frontend, backend, database, hosting, architecture style) move.
Evidence for 'small input changes must cause sensible, local output changes' (Section 8).

Usage: python tools/sensitivity.py [--details]
"""
import copy
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
from stacksense_engine.recommend import recommend  # noqa: E402

CORE = ("frontend", "backend", "database", "hosting")


def core(r):
    if not r.get("stack"):
        return {"status": r["status"]}
    out = {k: r["stack"][k]["choice"] for k in CORE}
    out["style"] = r["architecture_style"]
    return out


def perturbations(s):
    for k, v in s["priorities"].items():
        for d in (-1, 1):
            if 1 <= v + d <= 5:
                yield f"priorities.{k} {v}->{v + d}", ("priorities", k, v + d)
    for k, v in s["requirements"].items():
        if isinstance(v, bool):
            yield f"requirements.{k} {v}->{not v}", ("requirements", k, not v)
    yield "scale.users_12_months x1.2", ("scale", "users_12_months", int(s["scale"]["users_12_months"] * 1.2))
    yield "budget.monthly_infra_usd x1.2", ("budget", "monthly_infra_usd", round(s["budget"]["monthly_infra_usd"] * 1.2, 2))
    yield "timeline.mvp_weeks +2", ("timeline", "mvp_weeks", s["timeline"]["mvp_weeks"] + 2)
    yield "project.name renamed", ("project", "name", "Renamed project")


def analyse():
    rows, total, moved = [], 0, 0
    for i in range(1, 7):
        with open(os.path.join(ROOT, "scenarios", "public", f"P{i}.json"), encoding="utf-8") as f:
            s = json.load(f)
        base = core(recommend(s))
        for label, (sec, key, val) in perturbations(s):
            t = copy.deepcopy(s)
            t[sec][key] = val
            c = core(recommend(t))
            diff = [k for k in base if base.get(k) != c.get(k)]
            total += 1
            moved += len(diff)
            if diff:
                rows.append({"scenario": s["scenario_id"], "change": label, "moved": diff,
                             "to": {k: c.get(k) for k in diff}})
    summary = {"perturbations": total, "with_no_core_change": total - len(rows),
               "avg_core_decisions_moved": round(moved / total, 2),
               "max_core_decisions_moved": max((len(r["moved"]) for r in rows), default=0)}
    return summary, rows


if __name__ == "__main__":
    summary, rows = analyse()
    print(json.dumps(summary, indent=2))
    for r in rows:
        line = f"  {r['scenario']}: {r['change']:42} -> {', '.join(r['moved'])}"
        if "--details" in sys.argv:
            line += "  " + json.dumps(r["to"])
        print(line)
