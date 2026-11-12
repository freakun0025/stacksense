"""Orchestrator: validate -> profile -> pre-flight -> select layers -> cost -> budget re-plan -> warnings -> output.

Pure function of the input: no clock, randomness, network or LLM calls, so identical input gives
byte-identical output.
"""
import copy
import hashlib
import json
import traceback

from . import explain
from . import select_core as sc
from .architecture import decide
from .conflicts import preflight, analyse, relax_restricted
from .cost import estimate
from .kb import KB_VERSION, KB_AS_OF
from .profile import Profile
from .select_support import select_supporting
from .validate import validate

ENGINE_VERSION = "1.0.0"
STYLE_LABEL = {"static": "Static site", "monolith": "Monolith", "modular_monolith": "Modular monolith",
               "serverless": "Serverless/BaaS architecture", "service_oriented": "Service-oriented architecture",
               "microservices": "Microservices", "hybrid": "Hybrid architecture", "other": "Architecture"}
TRIGGER = {"cache": ["scale.peak_concurrent_users"], "queue": ["requirements.payments", "requirements.file_media_storage"],
           "search": ["requirements.full_text_search"], "auth": ["requirements.auth"], "sms": ["requirements.auth"],
           "storage": ["requirements.file_media_storage"], "cdn": ["requirements.seo_critical"],
           "realtime": ["requirements.realtime"], "realtime_crdt": ["project.type", "requirements.realtime"],
           "payments": ["requirements.payments"], "ml": ["requirements.ml_features"], "vector": ["requirements.ml_features"],
           "ml_training": ["requirements.ml_features"], "ci_cd": ["team.has_devops"], "mobile_ci": ["project.platforms"],
           "observability": ["requirements.availability"], "push": ["project.platforms"],
           "email": ["requirements.auth"], "offline_sync": ["requirements.offline_support"],
           "geospatial": ["project.description"], "security": ["compliance", "priorities.security"],
           "integration": ["infrastructure.existing_systems"], "iot": ["project.type"], "game_backend": ["project.type"],
           "analytics": ["project.type"]}


def _triggers(key, p):
    """Input fields that caused a supporting capability to be included (actual cause, not a static list)."""
    if key == "queue":
        t = [f for f, on in (("requirements.payments", p.payments), ("requirements.file_media_storage", p.files),
                             ("requirements.ml_features", p.ml != "none"), ("requirements.offline_support", p.offline),
                             ("requirements.notifications", bool(p.notifications)),
                             ("scale.workload", p.workload == "write_heavy")) if on]
        return t or ["requirements.background_jobs"]
    if key == "cache":
        t = [f for f, on in (("requirements.realtime", p.realtime), ("scale.peak_concurrent_users", p.tier_i >= 2),
                             ("requirements.p95_latency_ms", bool(p.p95 and p.p95 <= 200)),
                             ("scale.workload", p.workload == "read_heavy")) if on]
        return t or ["scale.users_12_months"]
    if key == "cdn":
        t = [f for f, on in (("requirements.seo_critical", p.seo), ("requirements.file_media_storage", p.files),
                             ("scale.users_12_months", p.tier_i >= 2), ("project.type", p.type == "content_site")) if on]
        return t or ["project.platforms"]
    if key == "email":
        return [f for f, on in (("requirements.notifications", "email" in p.notifications),
                                ("requirements.auth", p.auth == "email_password"),
                                ("project.description", "workflow" in p.signals)) if on]
    if key == "push":
        return [f for f, on in (("project.platforms", True), ("requirements.realtime", p.realtime),
                                ("requirements.notifications", "push" in p.notifications)) if on]
    return TRIGGER.get(key, [])


def input_hash(data):
    blob = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def _plan(p):
    fe = sc.select_frontend(p)
    be = sc.select_backend(p, fe)
    db = sc.select_database(p, be)
    host = sc.select_hosting(p, fe, be)
    off = sc.LayerResult("db_offering")
    notes = []
    if db.winner is not None:
        for eng in db.ranked:
            off = sc.select_offering(p, eng, host, be)
            if off.winner is not None:
                if eng is not db.winner:
                    notes.append(f"{db.winner.t['name']} scored highest but has no managed offering that satisfies the hard "
                                 f"constraints on {host.label}; fell back to {eng.t['name']}")
                    db.winner = eng
                break
    picks = select_supporting(p, fe, be, db, off, host)
    cost = estimate(p, fe, be, db, off, host, picks)
    return {"fe": fe, "be": be, "db": db, "off": off, "host": host, "picks": picks, "cost": cost, "notes": notes}


def _db_component(plan, p):
    db, off = plan["db"], plan["off"]
    if db.winner is None:
        return explain.none_component(db.none_reason, db.none_fields, db.none_alternatives)
    if off.winner is None:
        return {"choice": "None", "justification": "No database offering satisfies the hard constraints.",
                "driven_by": ["infrastructure.data_residency", "compliance"], "alternatives": [], "tradeoffs": [],
                "fit_score": None, "confidence": "low"}
    eng, o = db.winner, off.winner
    oname = o.t["name"]
    label = oname if eng.t["name"].split(" ")[0].lower() in oname.lower() else f"{eng.t['name']} on {oname}"
    if off.region_name:
        ha = ", HA standby" if (sc.ha_multiplier(o.t, p) > 1 and "ha" in o.t["traits"]
                                and "serverless" not in o.t["traits"]) else ""
        label += f" ({off.region_name}{ha})"
    comp = explain.component(label, eng, db.ranked, db.excluded, p)
    oj = [f.text for f in sorted(o.factors, key=lambda f: (-f.delta, f.text)) if f.delta >= 0.2][:2]
    if oj:
        comp["justification"] += f" Managed as {oname}: " + "; ".join(oj) + "."
    for f in explain.driven_by(o):
        if f not in comp["driven_by"]:
            comp["driven_by"].append(f)
    for a in explain.alternatives(o, off.ranked, off.excluded, oname, p, n=1, min_one=False):
        comp["alternatives"].append(a)
    comp["tradeoffs"] = (comp["tradeoffs"] + [t for t in explain.tradeoffs(o, p, 2) if t not in comp["tradeoffs"]])[:5]
    comp["engine"] = eng.t["name"]
    comp["offering"] = oname
    comp["kb_id"] = eng.id
    comp["offering_kb_id"] = o.id
    return comp


def _summary(p, style, plan, stack, cost):
    fe, be, host = plan["fe"], plan["be"], plan["host"]
    budget = f"${p.budget:,.0f}"
    band = (f"${cost['min']:,}/month" if cost["min"] == cost["max"]
            else f"${cost['min']:,}-{cost['max']:,}/month")
    fit = "within" if cost["max"] <= p.budget else "above" if cost["min"] > p.budget else "around"
    if style == "static":
        return (f"Static {stack['frontend']['choice']} site on {stack['hosting']['choice']} with no backend or database. "
                f"Estimated {band} ({fit} the {budget} budget).")
    parts = []
    if be.winner is not None:
        parts.append(explain.short(stack["backend"]["choice"]))
    if plan["db"].winner is not None and plan["off"].winner is not None and not (
            be.winner is not None and "baas" in be.winner.t["traits"]):
        parts.append(explain.short(stack["database"]["choice"]))
    client = stack["frontend"]["choice"]
    return (f"{STYLE_LABEL[style]}: {' + '.join(parts)} serving {client}, hosted on {stack['hosting']['choice']}. "
            f"Estimated {band} ({fit} the {budget} budget).")


def project_platforms(p):
    names = {"android": "Android", "ios": "iOS", "desktop": "desktop", "web": "web"}
    return "/".join(names.get(x, x) for x in p.platforms)


def _empty_cost(reason):
    return {"min": 0, "max": 0, "currency": "USD", "assumptions": [reason], "breakdown": []}


def recommend(raw, lenient=False, include_trace=True):
    try:
        return _recommend(raw, lenient, include_trace)
    except Exception as exc:  # never crash: surface as a structured error
        return {"scenario_id": raw.get("scenario_id") if isinstance(raw, dict) else None,
                "engine_version": ENGINE_VERSION, "status": "invalid_input",
                "summary": "The engine could not process this input.", "architecture_style": "other", "stack": None,
                "estimated_monthly_cost_usd": _empty_cost("Not estimated"), "warnings": [], "assumptions": [],
                "validation_errors": [{"field": "$", "message": f"internal error: {type(exc).__name__}: {exc}"}],
                "debug": traceback.format_exc().splitlines()[-3:]}


def _recommend(raw, lenient, include_trace):
    v = validate(raw, lenient=lenient)
    sid = raw.get("scenario_id") if isinstance(raw, dict) else None
    base = {"scenario_id": sid, "engine_version": ENGINE_VERSION, "kb_version": f"{KB_VERSION} (as of {KB_AS_OF})",
            "input_hash": input_hash(raw) if isinstance(raw, dict) else None}
    if v["errors"]:
        n = len(v["errors"])
        return {**base, "status": "invalid_input",
                "summary": f"Input is invalid: {n} field error{'s' if n != 1 else ''}. Fix them and re-run; no stack was generated.",
                "architecture_style": "other", "stack": None,
                "estimated_monthly_cost_usd": _empty_cost("Not estimated: input is invalid"),
                "warnings": [], "assumptions": v["assumptions"], "validation_errors": v["errors"], "llm_used": False}

    data = v["data"]
    assumptions = list(v["assumptions"])
    p = Profile(data, assumptions)
    relax_restricted(p)
    infeasible, pre_warn, options = preflight(p)
    if infeasible:
        return {**base, "status": "infeasible",
                "summary": "The hard constraints contradict each other, so no compliant stack exists. "
                           "See critical warnings and resolution_options.",
                "architecture_style": "other", "stack": None,
                "estimated_monthly_cost_usd": _empty_cost("Not estimated: constraints are infeasible"),
                "warnings": pre_warn, "assumptions": assumptions, "validation_errors": [],
                "resolution_options": options, "profile": p.summary(), "llm_used": False}

    plan = _plan(p)
    if plan["cost"]["min"] > p.budget and p.prio["cost"] < 5:
        p2 = Profile(copy.deepcopy(data), [])
        relax_restricted(p2)
        p2.prio["cost"] = 5
        p2.cost_replan = True
        plan2 = _plan(p2)
        if plan2["cost"]["min"] < plan["cost"]["min"]:
            assumptions.append(f"Budget re-plan: the first plan's floor (~${plan['cost']['min']:,}/month) exceeded "
                               f"budget.monthly_infra_usd=${p.budget:,.0f}, so the engine re-ran with cost weighted at 5 "
                               f"(input priorities.cost={p.prio['cost']}) and kept the cheaper plan "
                               f"(~${plan2['cost']['min']:,}/month)")
            p, plan = p2, plan2
        else:
            assumptions.append(f"Budget re-plan attempted (cost weighted at 5) but no cheaper compliant plan exists")
    assumptions.extend(plan["notes"])
    fe, be, db, off, host, picks, cost = (plan[k] for k in ("fe", "be", "db", "off", "host", "picks", "cost"))

    stack = {"frontend": explain.frontend_component(fe, p)}
    if be.winner is None:
        stack["backend"] = explain.none_component(be.none_reason, be.none_fields, be.none_alternatives)
    else:
        stack["backend"] = explain.component(be.label or be.winner.t["name"], be.winner, be.ranked, be.excluded, p)
    stack["database"] = _db_component(plan, p)
    if host.winner is None:
        stack["hosting"] = {"choice": "None", "justification": "No hosting option satisfies the hard constraints.",
                            "driven_by": ["infrastructure.deployment_model"], "alternatives": [], "tradeoffs": [],
                            "fit_score": None, "confidence": "low"}
    elif host.winner.t["layer"] != "hosting":
        # mobile-only app on a BaaS: the BaaS is the platform
        alt_host = next((c for c in host.ranked[1:] if c.t["layer"] == "hosting"), None)
        alts = []
        if alt_host is not None:
            alts.append({"choice": sc.hosting_label(alt_host, p, "app")[0],
                         "why_not": "Only needed once custom server code outgrows the BaaS's edge functions; today it "
                                    "would be a deployment target with nothing to deploy."})
        hard = [e for e in host.excluded if e.excluded[1] and e.excluded[1][0] in explain.HARD_FIELDS]
        if hard:
            alts.append({"choice": hard[0].t["name"], "why_not": f"Excluded by hard constraint: {hard[0].excluded[0]}."})
        stack["hosting"] = {
            "choice": host.label,
            "justification": (f"The {project_platforms(p)} app talks directly to {host.winner.t['name'].split(' (')[0]} "
                              f"(database, auth, storage and functions are all managed in "
                              f"{host.region_name or 'the chosen region'}), so there is no web tier or server to host."),
            "driven_by": ["project.platforms", "infrastructure.data_residency", "team.has_devops"],
            "alternatives": alts, "tradeoffs": explain.tradeoffs(host.winner, p, 2),
            "fit_score": None, "confidence": "high", "kb_id": host.winner.id}
    else:
        stack["hosting"] = explain.component(host.label, host.winner, host.ranked, host.excluded, p)
    supporting = []
    for pk in picks:
        if pk.winner is None:
            continue
        comp = explain.component(pk.label, pk.winner, pk.ranked, pk.excluded, p)
        trig = _triggers(pk.key, p)
        comp["driven_by"] = (trig + [f for f in comp["driven_by"] if f not in trig])[:7]
        entry = {"layer": pk.layer}
        if pk.purpose:
            entry["purpose"] = pk.purpose
        entry.update(comp)
        supporting.append(entry)
    stack["supporting"] = supporting

    style, style_why, style_fields = decide(p, fe, be, host)
    warnings, relax = analyse(p, fe, be, db, off, host, picks, cost, v["unknown_fields"], v["notes"])
    warnings = pre_warn + warnings
    assumptions.extend(relax)
    status = "ok"
    if any(w["severity"] in ("warning", "critical") for w in warnings):
        status = "ok_with_warnings"

    out = {**base, "status": status, "summary": _summary(p, style, plan, stack, cost),
           "architecture_style": style,
           "architecture_rationale": {"text": style_why, "driven_by": style_fields},
           "stack": stack, "estimated_monthly_cost_usd": cost, "warnings": warnings,
           "assumptions": _uniq(assumptions), "validation_errors": [], "profile": p.summary(), "llm_used": False}
    if include_trace:
        out["decision_trace"] = {
            "frontend": [r for part, c, ok, ex, _ in fe.parts for r in explain.trace(ok, ex, top=4)],
            "backend": explain.trace(be.ranked, be.excluded),
            "database": explain.trace(db.ranked, db.excluded),
            "database_offering": explain.trace(off.ranked, off.excluded),
            "hosting": explain.trace(host.ranked, host.excluded),
        }
    return out


def _uniq(xs):
    out = []
    for x in xs:
        if x not in out:
            out.append(x)
    return out


def to_json(result):
    return json.dumps(result, indent=2, ensure_ascii=False)
