"""Property-based checks over randomly generated scenarios (seeded -> reproducible).

For every generated scenario it asserts:
  1. the engine never crashes and always returns a valid status;
  2. determinism: two runs give byte-identical JSON;
  3. no chosen component violates a hard constraint (residency, compliance, deployment model,
     cloud preference, lifecycle) - re-checked independently against the knowledge base;
  4. budget is never exceeded silently (BUDGET_EXCEEDED warning whenever min cost > budget);
  5. no microservices / Kubernetes for small teams (over-engineering guard);
  6. status 'ok' never carries warning/critical items.

Usage: python tools/fuzz.py [N] [SEED]
"""
import json
import os
import random
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from stacksense_engine import schema as S  # noqa: E402
from stacksense_engine.kb import BY_ID  # noqa: E402
from stacksense_engine.profile import Profile  # noqa: E402
from stacksense_engine.conflicts import relax_restricted  # noqa: E402
from stacksense_engine.recommend import recommend  # noqa: E402
from stacksense_engine.scoring import hard_exclusion  # noqa: E402

LANG_POOL = ["javascript", "typescript", "python", "java", "kotlin", "csharp", "go", "php", "ruby", "sql", "dart",
             "swift", "rust", "elixir"]


def random_scenario(rng, i):
    users12 = rng.choice([50, 800, 3000, 20000, 80000, 400000, 2_000_000, 8_000_000])
    plats = rng.sample(S.PLATFORMS, rng.choice([1, 1, 1, 2, 2, 3]))
    if "api_only" in plats and rng.random() < 0.7:
        plats = ["api_only"]
    return {
        "scenario_id": f"F{i:05d}",
        "project": {"name": f"Fuzz {i}", "type": rng.choice(S.PROJECT_TYPES),
                    "description": rng.choice(["", "Users chat and upload photos", "Ledger for loans with UPI payouts",
                                               "Offline survey app with GPS photos on low-end phones",
                                               "Static marketing pages in Markdown", "Internal approvals for employees"]),
                    "platforms": plats},
        "scale": {"users_at_launch": max(1, users12 // rng.choice([1, 5, 20])), "users_12_months": users12,
                  "peak_concurrent_users": max(1, int(users12 * rng.choice([0.01, 0.05, 0.2]))),
                  "traffic_pattern": rng.choice(S.TRAFFIC), "workload": rng.choice(S.WORKLOAD),
                  "data_volume_gb_12_months": rng.choice([1, 20, 200, 2000, 20000])},
        "team": {"size": rng.choice([1, 2, 3, 5, 8, 15, 30]), "experience": rng.choice(S.EXPERIENCE),
                 "languages": rng.sample(LANG_POOL, rng.choice([0, 1, 2, 3])), "has_devops": rng.random() < 0.4},
        "budget": {"monthly_infra_usd": rng.choice([0, 20, 100, 300, 1500, 6000, 30000])},
        "timeline": {"mvp_weeks": rng.choice([2, 4, 8, 12, 26])},
        "infrastructure": {"cloud_preference": rng.choice(S.CLOUD), "deployment_model": rng.choice(
            ["managed_cloud"] * 5 + ["self_hosted_cloud_vm", "on_premise", "air_gapped"]),
            "data_residency": rng.choice(["none", "none", "india", "eu", "us", "other"]),
            "existing_systems": rng.sample(["Heroku", "On-prem SQL Server 2019", "Microsoft 365", "MySQL 5.7",
                                            "Okta", "SAP ERP", "Node.js 16"], rng.choice([0, 0, 1, 2]))},
        "requirements": {"realtime": rng.random() < 0.3, "offline_support": rng.random() < 0.15,
                         "full_text_search": rng.random() < 0.3, "file_media_storage": rng.random() < 0.4,
                         "payments": rng.random() < 0.35, "auth": rng.choice(S.AUTH),
                         "multi_tenant": rng.random() < 0.2, "ml_features": rng.choice(S.ML + ["none"] * 3),
                         "seo_critical": rng.random() < 0.3, "availability": rng.choice(S.AVAILABILITY),
                         "p95_latency_ms": rng.choice([None, 30, 100, 300, 800])},
        "compliance": rng.sample(S.COMPLIANCE, rng.choice([0, 0, 1, 2, 3])),
        "priorities": {k: rng.randint(1, 5) for k in S.PRIORITY_KEYS},
    }


def chosen_components(out):
    st = out["stack"]
    items = []
    for c in st["frontend"].get("components", []):
        items.append(("frontend", c["kb_id"]))
    for k in ("backend", "hosting"):
        if st[k].get("kb_id"):
            items.append((k, st[k]["kb_id"]))
    if st["database"].get("kb_id"):
        items.append(("database", st["database"]["kb_id"]))
        items.append(("db_offering", st["database"]["offering_kb_id"]))
    for s in st["supporting"]:
        if s.get("kb_id"):
            items.append((s["layer"], s["kb_id"]))
    return items


def check(scn):
    problems = []
    a = recommend(scn)
    b = recommend(json.loads(json.dumps(scn)))
    if json.dumps(a, sort_keys=True) != json.dumps(b, sort_keys=True):
        problems.append("non-deterministic output")
    if a["status"] not in ("ok", "ok_with_warnings", "infeasible", "invalid_input"):
        problems.append(f"bad status {a['status']}")
    if a["status"] == "invalid_input" and any(e["field"] == "$" for e in a["validation_errors"]):
        problems.append("internal error: " + a["validation_errors"][0]["message"])
    if a["status"] == "ok" and any(w["severity"] != "info" for w in a["warnings"]):
        problems.append("status ok with non-info warnings")
    if a["stack"]:
        p = Profile(json.loads(json.dumps(scn)), [])
        relax_restricted(p)
        static_or_baas = a["architecture_style"] in ("static", "serverless")
        for layer, kid in chosen_components(a):
            t = BY_ID.get(kid)
            if t is None:
                problems.append(f"unknown kb id {kid}")
                continue
            if t["status"] != "active":
                problems.append(f"deprecated component chosen: {kid}")
            pii = False if (layer == "hosting" and static_or_baas) else None
            if t["layer"] == "backend" and layer == "hosting":
                pii = None
            ex = hard_exclusion(t, p, pii=pii)
            if ex:
                problems.append(f"hard constraint violated by {kid} ({layer}): {ex[0]}")
        cost = a["estimated_monthly_cost_usd"]
        if cost["min"] > p.budget and not any(w["code"] == "BUDGET_EXCEEDED" for w in a["warnings"]):
            problems.append("budget exceeded silently")
        if a["architecture_style"] == "microservices" and p.team_size < 25:
            problems.append("microservices for a small team")
        no_managed_option = p.restricted and (p.ha >= 3 or p.tier_i >= 3)   # on-prem at extreme scale/HA
        if a["stack"]["hosting"].get("kb_id") in ("kubernetes", "onprem_k8s") and p.team_size < 4 \
                and not p.has_devops and not no_managed_option:
            problems.append("kubernetes for a tiny team without devops")
        if no_managed_option and not p.has_devops and not any(w["severity"] == "critical" for w in a["warnings"]) \
                and p.ha >= 3:
            problems.append("extreme on-prem requirement without a critical warning")
        for k in ("frontend", "backend", "database", "hosting"):
            comp = a["stack"][k]
            if not comp.get("driven_by"):
                problems.append(f"{k} has empty driven_by")
            if comp["choice"] != "None" and not comp.get("alternatives"):
                problems.append(f"{k} has no alternatives")
    return a, problems


def run_fuzz(n=500, seed=2026):
    rng = random.Random(seed)
    stats = {"scenarios": n, "ok": 0, "ok_with_warnings": 0, "infeasible": 0, "invalid_input": 0, "failures": []}
    t0 = time.time()
    for i in range(n):
        scn = random_scenario(rng, i)
        out, problems = check(scn)
        stats[out["status"]] += 1
        if problems:
            stats["failures"].append({"scenario_id": scn["scenario_id"], "problems": problems})
    stats["seconds"] = round(time.time() - t0, 1)
    stats["ms_per_scenario"] = round(1000 * (time.time() - t0) / max(n, 1) / 2, 1)
    return stats


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 2026
    st = run_fuzz(n, seed)
    fails = st.pop("failures")
    print(json.dumps(st, indent=2))
    print(f"failures: {len(fails)}")
    for f in fails[:25]:
        print(" ", f["scenario_id"], "; ".join(f["problems"][:3]))
    sys.exit(1 if fails else 0)
