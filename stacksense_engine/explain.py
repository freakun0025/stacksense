"""Turns scored candidates into output components (justification, driven_by, alternatives, trade-offs)."""
import re

from .kb.sources import SOURCES

INPUT_PREFIXES = ("project.", "scale.", "team.", "budget.", "timeline.", "infrastructure.", "requirements.",
                  "compliance", "priorities.")
HARD_FIELDS = ("infrastructure.data_residency", "compliance", "infrastructure.deployment_model",
               "infrastructure.cloud_preference")
LIMIT_FILTERS = [
    (r"india", lambda p: p.region == "india" or p.effective_residency == "india"),
    (r"hipaa", lambda p: "hipaa" in p.compliance),
    (r"websocket", lambda p: p.realtime),
    (r"low-end", lambda p: p.low_end),
    (r"\bios\b", lambda p: p.ios),
    (r"\bseo\b", lambda p: p.seo),
    (r"mumbai", lambda p: p.region == "india"),
    (r"cold start", lambda p: p.traffic != "steady" or p.p95 is not None),
    (r"per-mau|mau", lambda p: p.users > 10_000),
    (r"residency", lambda p: p.effective_residency != "none"),
    (r"non-commercial", lambda p: not (p.type == "content_site" and p.team_size == 1)),
]


FIELD_LABEL = {
    "priorities.time_to_market": "time-to-market", "priorities.cost": "cost", "priorities.scalability": "scalability",
    "priorities.performance": "performance", "priorities.maintainability": "maintainability",
    "priorities.security": "security", "team.languages": "team skills", "team.experience": "learning curve",
    "team.has_devops": "operational simplicity", "requirements.realtime": "realtime support",
    "requirements.seo_critical": "SEO", "requirements.offline_support": "offline support",
    "project.platforms": "platform coverage", "project.type": "fit for the project type",
    "project.description": "fit for the described use case", "budget.monthly_infra_usd": "budget fit",
    "requirements.availability": "availability", "scale.traffic_pattern": "traffic elasticity",
    "infrastructure.existing_systems": "reuse of existing systems", "hosting": "integration with the hosting platform",
    "backend": "integration with the backend", "frontend": "integration with the frontend",
    "database": "integration with the database", "requirements.auth": "authentication fit",
    "requirements.multi_tenant": "multi-tenancy", "scale.users_12_months": "fit for the user scale",
    "requirements.payments": "payments fit", "requirements.ml_features": "ML fit",
    "infrastructure.vendor_lock_in_tolerance": "portability", "requirements.full_text_search": "search fit",
    "infrastructure.data_residency": "data residency", "scale.peak_concurrent_users": "concurrency handling",
}


def is_input(field):
    return field.startswith(INPUT_PREFIXES)


def _cap(s):
    if not s:
        return s
    first = s.split(" ", 1)[0]
    if "." in first.rstrip(".:,;") or "_" in first:   # starts with a field path or identifier: keep as is
        return s
    return s[:1].upper() + s[1:]


def short(label):
    return label.split(" (")[0]


def justification(c):
    pos = sorted([f for f in c.factors if f.delta >= 0.2], key=lambda f: (-f.delta, f.text))
    texts, seen = [], set()
    for f in pos:
        if f.text not in seen:
            seen.add(f.text)
            texts.append(f.text)
        if len(texts) == 4:
            break
    s = ("Chosen because " + "; ".join(texts) + ".") if texts else "Best remaining fit after hard constraints."
    neg = sorted([f for f in c.factors if f.delta <= -0.6], key=lambda f: (f.delta, f.text))
    if neg:
        s += f" Accepted trade-off: {neg[0].text}."
    return s


def driven_by(c, extra=()):
    agg = {}
    for f in c.factors:
        for fld in f.fields:
            if is_input(fld):
                agg[fld] = agg.get(fld, 0.0) + abs(f.delta)
    ordered = sorted(agg.items(), key=lambda kv: (-round(kv[1], 3), kv[0]))
    out = [k for k, v in ordered if v >= 0.3][:6]
    for e in extra:
        if e not in out:
            out.append(e)
    if not out:
        out = [k for k, _ in ordered[:2]] or ["priorities.time_to_market"]
    return out


def why_not(winner, alt, winner_label):
    wf, af = winner.field_deltas(), alt.field_deltas()
    diffs = []
    for fld in sorted(set(wf) | set(af)):
        d = wf.get(fld, 0.0) - af.get(fld, 0.0)
        if d > 0.25:
            diffs.append((round(d, 3), fld))
    diffs.sort(key=lambda x: (-x[0], x[1]))
    weak, stronger = [], []
    for _, fld in diffs[:3]:
        neg = sorted([f for f in alt.factors if f.fields[0] == fld and f.delta < 0], key=lambda f: (f.delta, f.text))
        if neg:
            if len(weak) < 2:
                weak.append(neg[0].text)
        else:
            stronger.append(FIELD_LABEL.get(fld, fld.split(".")[-1].replace("_", " ")))
    parts = []
    if weak:
        parts.append(_cap("; ".join(weak)))
    if stronger:
        parts.append(f"{short(winner_label)} scores higher on {' and '.join(stronger[:2])}")
    why = ". ".join(parts) if parts else "A close runner-up with a slightly weaker overall fit"
    return f"{why} (fit {alt.score:.1f} vs {winner.score:.1f})."


def alternatives(winner, ranked, excluded, winner_label, p, n=2, suffix="", min_one=True):
    alts = []
    for alt in ranked[1:1 + n]:
        if alt.id == winner.id:
            continue
        alts.append({"choice": alt.t["name"] + suffix, "why_not": why_not(winner, alt, winner_label)})
    hard = [e for e in excluded if e.excluded[1] and e.excluded[1][0] in HARD_FIELDS]
    hard.sort(key=lambda e: (-e.t["mature"], -sum(e.t["scores"].values()), e.id))
    if hard:
        e = hard[0]
        alts.append({"choice": e.t["name"] + suffix, "why_not": f"Excluded by hard constraint: {e.excluded[0]}."})
    life = [e for e in excluded if e.excluded[1] and e.excluded[1][0] == "knowledge_base.lifecycle" and _mentioned(e, p)]
    for e in life[:1]:
        alts.append({"choice": e.t["name"] + suffix, "why_not": f"Not recommended - {e.excluded[0]}"})
    if not alts and min_one and excluded:
        e = sorted(excluded, key=lambda e: (-e.t["mature"], e.id))[0]
        alts.append({"choice": e.t["name"] + suffix, "why_not": f"Not applicable: {e.excluded[0]}."})
    return alts


def _mentioned(e, p):
    text = (" ".join(p.existing) + " " + p.description).lower()
    return any(re.search(pat, text) for pat in e.t["aliases"])


def tradeoffs(c, p, limit=4):
    out = []
    for lim in c.t["limits"]:
        skip = False
        for pat, pred in LIMIT_FILTERS:
            if re.search(pat, lim.lower()) and not pred(p):
                skip = True
                break
        if not skip:
            out.append(lim)
    for f in sorted([f for f in c.factors if f.delta <= -0.5], key=lambda f: (f.delta, f.text)):
        t = _cap(f.text)
        if t not in out and not any(o.lower()[:24] == t.lower()[:24] for o in out):
            out.append(t)
    for n in c.notes:
        if _cap(n) not in out:
            out.append(_cap(n))
    return out[:limit]


def confidence(ranked):
    if len(ranked) < 2:
        return "high"
    m = ranked[0].score - ranked[1].score
    return "high" if m >= 2.0 else "medium" if m >= 0.8 else "low"


def sources(c, n=3):
    return [SOURCES[s]["url"] for s in c.t["src"][:n] if s in SOURCES]


def component(label, c, ranked, excluded, p, extra_driven=(), extra_trade=(), suffix=""):
    d = {
        "choice": label,
        "justification": justification(c),
        "driven_by": driven_by(c, extra_driven),
        "alternatives": alternatives(c, ranked, excluded, label, p, suffix=suffix),
        "tradeoffs": (list(extra_trade) + tradeoffs(c, p))[:5],
        "fit_score": c.score,
        "confidence": confidence(ranked),
        "kb_id": c.id,
    }
    if c.t.get("version"):
        d["version"] = c.t["version"]
    src = sources(c)
    if src:
        d["sources"] = src
    return d


def none_component(reason, fields, alts):
    return {"choice": "None", "justification": reason, "driven_by": list(fields), "alternatives": list(alts),
            "tradeoffs": ["Add a server tier later only if dynamic features (forms, auth, comments) appear"],
            "fit_score": None, "confidence": "high"}


def frontend_component(fe, p):
    if not fe.parts:
        return none_component(fe.none_reason, fe.none_fields,
                              [{"choice": "Developer portal (docs site)",
                                "why_not": "optional; OpenAPI docs can be generated from the API itself"}])
    just, drivers, alts, trades, srcs = [], [], [], [], []
    for part, cand, ranked, excluded, plats in fe.parts:
        tag = {"web": "Web", "mobile": "Mobile", "desktop": "Desktop"}[part]
        just.append(f"{tag} - {cand.t['name']}: {justification(cand)}")
        for f in driven_by(cand):
            if f not in drivers:
                drivers.append(f)
        plat_txt = " + ".join(x.capitalize() if x != "ios" else "iOS" for x in plats)
        sfx = f" for {plat_txt}" if part == "mobile" else " (desktop)" if part == "desktop" else (
            " (web)" if len(fe.parts) > 1 else "")
        for a in alternatives(cand, ranked, excluded, cand.t["name"], p, n=1 if len(fe.parts) > 1 else 2, suffix=sfx):
            alts.append(a)
        trades.extend(tradeoffs(cand, p, limit=2))
        srcs.extend(sources(cand, 2))
    primary = fe.parts[0]
    return {"choice": fe.label, "justification": " ".join(just), "driven_by": drivers[:8], "alternatives": alts,
            "tradeoffs": trades[:5], "fit_score": primary[1].score, "confidence": confidence(primary[2]),
            "components": [{"platform": " + ".join(pl), "choice": c.t["name"], "version": c.t.get("version", ""),
                            "kb_id": c.id}
                           for _, c, _, _, pl in fe.parts],
            "sources": srcs[:5]}


def trace(ranked, excluded, top=6, label_fn=None):
    rows = []
    for i, c in enumerate(ranked[:top]):
        rows.append({"choice": label_fn(c) if label_fn else c.t["name"], "score": c.score,
                     "status": "selected" if i == 0 else "candidate",
                     "top_factors": [f"{'+' if f.delta > 0 else ''}{f.delta:.2f} {f.text}"
                                     for f in sorted(c.factors, key=lambda f: (-abs(f.delta), f.text))[:4]]})
    for c in excluded[:top]:
        rows.append({"choice": c.t["name"], "score": None, "status": "excluded", "reason": c.excluded[0],
                     "fields": c.excluded[1]})
    return rows
