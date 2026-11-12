"""Scoring primitives.

A candidate's score is the sum of explicit *factors*. Each factor records the input fields that
caused it, a signed weight and a human sentence, so every decision is traceable
(``driven_by``, justification, why-not for alternatives, decision trace).

Hard constraints never become factors: they exclude a candidate outright with a reason.
"""
import math
import re

HYPERSCALERS = ("aws", "gcp", "azure")
CLOUD_LABEL = {"aws": "AWS", "gcp": "Google Cloud", "azure": "Azure"}
MULTICLOUD_SAAS = ("mongodb", "clickhouse", "timescale", "cockroach", "elastic")
NEUTRAL_PROVIDERS = (None, "self", "host", "any", "vm", "hyperscaler", "cloud")
INFRA_LAYERS = ("hosting", "db_offering", "cache", "queue", "storage", "cdn", "search", "ml", "realtime", "security",
                "iot", "offline_sync", "vector", "ml_training", "integration", "backend", "database", "auth")
RES_LABEL = {"india": "India", "eu": "EU", "us": "US", "other": "in-country"}
COMP_LABEL = {"gdpr": "GDPR DPA", "dpdp": "DPDP-compliant processing", "hipaa": "HIPAA BAA", "pci_dss": "PCI DSS",
              "rbi_localisation": "RBI data-localisation (India-only storage)", "soc2": "SOC 2", "iso27001": "ISO 27001"}
PRIO_LABEL = {"cost": "cost efficiency", "time_to_market": "time-to-market", "scalability": "scalability",
              "performance": "performance", "maintainability": "maintainability", "security": "security"}
LANG_NEAR = {("javascript", "typescript"): 0.85, ("typescript", "javascript"): 0.9, ("java", "kotlin"): 0.8,
             ("kotlin", "java"): 0.8, ("csharp", "fsharp"): 0.7, ("fsharp", "csharp"): 0.8}
_CORE_DATA = {"hosting", "db_offering", "database", "backend", "storage", "auth"}
# Which layers each regime constrains (None = every layer that touches personal data).
COMPLIANCE_SCOPE = {
    "gdpr": None, "dpdp": None,
    "hipaa": _CORE_DATA | {"search", "cache", "queue", "ml", "realtime", "observability", "email", "offline_sync", "vector"},
    "pci_dss": _CORE_DATA | {"payments", "cache", "queue"},
    "rbi_localisation": _CORE_DATA | {"payments", "cache", "queue", "search", "observability", "ml"},
    "soc2": _CORE_DATA | {"payments"},
    "iso27001": _CORE_DATA | {"payments"},
}
STATUS_LABEL = {"deprecated": "Deprecated", "eol": "End of life", "maintenance": "Maintenance mode",
                "closed_to_new": "Closed to new customers"}


class Factor:
    __slots__ = ("fields", "delta", "text", "kind")

    def __init__(self, fields, delta, text, kind="soft"):
        self.fields = [fields] if isinstance(fields, str) else list(fields)
        self.delta = round(float(delta), 4)
        self.text = text
        self.kind = kind


class Cand:
    def __init__(self, tech, label=None):
        self.t = tech
        self.id = tech["id"]
        self.label = label or tech["name"]
        self.factors = []
        self.excluded = None          # (reason, fields)
        self.notes = []

    def add(self, fields, delta, text, kind="soft"):
        if abs(delta) >= 0.005:
            self.factors.append(Factor(fields, delta, text, kind))

    @property
    def score(self):
        return round(sum(f.delta for f in self.factors), 3)

    def field_deltas(self):
        out = {}
        for f in self.factors:
            key = f.fields[0]
            out[key] = round(out.get(key, 0) + f.delta, 4)
        return out


def rank(cands):
    """Deterministic ordering: score desc, maturity desc, id asc."""
    ok = [c for c in cands if not c.excluded]
    ok.sort(key=lambda c: (-c.score, -c.t["mature"], c.id))
    ex = [c for c in cands if c.excluded]
    ex.sort(key=lambda c: (-c.t["mature"], c.id))
    return ok, ex


# ------------------------------------------------------------------ hard constraints
def hard_exclusion(t, p, pii=None):
    """Return (reason, fields) if `t` violates a hard constraint for profile `p`, else None."""
    if t["status"] != "active":
        return (f"{STATUS_LABEL.get(t['status'], t['status'])}: {t['status_note']}", ["knowledge_base.lifecycle"])
    pii = t["pii"] if pii is None else pii
    prov = t["provider"]
    layer = t["layer"]
    traits = t["traits"]
    # --- deployment model
    if p.restricted:
        if not t["self_host"] and layer not in ("mobile_ci",):
            return (f"deployment_model={p.deployment} allows only self-hostable components; {t['name']} is a managed/SaaS service",
                    ["infrastructure.deployment_model"])
        if layer == "hosting" and "onprem" not in traits:
            return (f"deployment_model={p.deployment} requires hosting inside your own data centre",
                    ["infrastructure.deployment_model"])
        if p.air_gapped and layer == "cdn":
            return ("air-gapped networks cannot use a CDN", ["infrastructure.deployment_model"])
    else:
        if layer == "hosting" and "onprem" in traits:
            return (f"deployment_model={p.deployment} is not on-premise", ["infrastructure.deployment_model"])
    if p.deployment == "managed_cloud" and layer in ("hosting", "db_offering") and t["self_host"] \
            and t["id"] != "sqlite_embedded":
        return ("deployment_model=managed_cloud: self-managed VMs/databases are excluded in favour of managed services",
                ["infrastructure.deployment_model"])
    if p.vm_only:
        if layer == "hosting" and t["id"] != "vm_compose":
            return ("deployment_model=self_hosted_cloud_vm: the stack runs on your own cloud VMs",
                    ["infrastructure.deployment_model"])
        if layer in ("db_offering", "cache", "queue", "search", "storage", "backend") and not t["self_host"]:
            return ("deployment_model=self_hosted_cloud_vm: managed data services are excluded; run it on the VMs",
                    ["infrastructure.deployment_model"])
    # --- cloud preference
    if layer in INFRA_LAYERS:
        if p.cloud in HYPERSCALERS:
            if prov in HYPERSCALERS and prov != p.cloud:
                return (f"cloud_preference={p.cloud}: {t['name']} is a {CLOUD_LABEL[prov]} service",
                        ["infrastructure.cloud_preference"])
            if prov not in HYPERSCALERS and prov not in NEUTRAL_PROVIDERS and prov not in MULTICLOUD_SAAS \
                    and layer not in ("auth",) and not t["self_host"]:
                return (f"cloud_preference={p.cloud}: {t['name']} runs outside {CLOUD_LABEL[p.cloud]}",
                        ["infrastructure.cloud_preference"])
        if p.cloud == "none" and not t["self_host"] and prov not in (None, "self", "host"):
            return ("cloud_preference=none: no public-cloud services", ["infrastructure.cloud_preference"])
    # --- residency
    res = p.effective_residency
    if pii and res != "none":
        self_placed = t["self_host"] and prov in NEUTRAL_PROVIDERS
        if not self_placed and res not in t["regions"]:
            field = "compliance" if (res == "india" and p.residency == "none") else "infrastructure.data_residency"
            why = "cannot pin data location" if not t["regions"] else f"no {RES_LABEL[res]} region"
            return (f"{why} ({field}={'rbi_localisation' if field == 'compliance' else res})", [field])
    # --- compliance (only for layers inside that regime's scope)
    if pii and p.compliance:
        self_placed = t["self_host"] and prov in NEUTRAL_PROVIDERS
        if not self_placed and prov is not None:
            comp = set(t["compliance"])
            for c in p.compliance:
                scope = COMPLIANCE_SCOPE.get(c)
                if scope is not None and layer not in scope:
                    continue
                ok = c in comp or (c == "dpdp" and "gdpr" in comp)
                if c == "rbi_localisation":
                    ok = ("rbi_localisation" in comp or prov in HYPERSCALERS) and "india" in t["regions"]
                if not ok:
                    return (f"lacks {COMP_LABEL[c]} (compliance includes {c})", ["compliance"])
    return None


# ------------------------------------------------------------------ common soft factors
def lang_match(tech_langs, team_langs):
    if not tech_langs or not team_langs:
        return None, None
    best, best_lang = 0.0, None
    for tl in tech_langs:
        for ml in team_langs:
            v = 1.0 if tl == ml else LANG_NEAR.get((ml, tl), 0.0)
            if v > best:
                best, best_lang = v, tl
    return best, best_lang


def skill_fit(c, p, weight=1.0, lang_override=None):
    t = c.t
    langs = lang_override or t["langs"]
    if not langs:
        return
    if not p.langs:
        if t["learn"] <= 2:
            c.add("team.languages", -0.4 * weight, "no team languages given, so steep-learning-curve options are avoided")
        return
    m, lang = lang_match(langs, p.langs)
    w = {"beginner": 2.6, "intermediate": 2.0, "mixed": 1.8, "senior": 1.4}[p.exp] * weight
    w *= 1.2 if p.weeks <= 6 else 1.0
    w *= 0.7 + 0.1 * p.prio["time_to_market"]
    if m >= 1.0:
        c.add("team.languages", w, f"team already works in {lang} (team.languages)")
    elif m > 0:
        known = ", ".join(sorted(p.langs))
        c.add("team.languages", w * m * 0.8, f"close to the team's skills: {lang} is a short step from {known}")
    else:
        need = "/".join(langs[:2])
        c.add("team.languages", -w * 0.9, f"no {need} in team.languages: ramp-up time and hiring risk")


def learning_fit(c, p):
    t = c.t
    k = {"beginner": 0.6, "intermediate": 0.3, "mixed": 0.35, "senior": 0.1}[p.exp]
    if p.weeks <= 4:
        k += 0.2
    d = (t["learn"] - 3) * k
    if d > 0:
        c.add("team.experience", d, f"gentle learning curve suits a {p.exp} team on a {p.weeks}-week timeline")
    elif d < 0:
        c.add("team.experience", d, f"steep learning curve for a {p.exp} team")


def ops_fit(c, p, weight=1.0):
    t = c.t
    if not p.has_devops:
        d = -max(0, t["ops"] - 2) * (0.9 if p.team_size <= 5 else 0.6) * weight
        if d:
            c.add("team.has_devops", d, f"needs ongoing operations work but team.has_devops=false (ops burden {t['ops']}/5)")
        elif t["ops"] <= 1:
            c.add("team.has_devops", 0.4 * weight, "fully managed: no operations work for a team without DevOps")
    else:
        d = -max(0, t["ops"] - 3) * 0.4 * weight
        if d:
            c.add("team.has_devops", d, f"high operational burden ({t['ops']}/5) even with DevOps support")


def priority_fit(c, p, weight=0.55, keys=None, dimw=None):
    t = c.t
    for key in keys or ("cost", "time_to_market", "scalability", "performance", "maintainability", "security"):
        pr = p.prio[key]
        s = t["scores"][key]
        d = weight * (pr / 3.0) * (s - 3) * ((dimw or {}).get(key, 1.0))
        if key == "cost" and getattr(p, "cost_replan", False):
            pr = f"{pr} (budget re-plan)"
        if abs(d) < 0.01:
            continue
        if d > 0:
            c.add(f"priorities.{key}", d, f"strong {PRIO_LABEL[key]} ({s}/5) with priorities.{key}={pr}")
        else:
            c.add(f"priorities.{key}", d, f"weaker {PRIO_LABEL[key]} ({s}/5) with priorities.{key}={pr}")


def maturity_fit(c, p):
    d = (c.t["mature"] - 3) * 0.15 * (p.prio["maintainability"] / 3.0)
    if d > 0:
        c.add("priorities.maintainability", d, "mature, widely adopted technology with a large ecosystem")
    elif d < 0:
        c.add("priorities.maintainability", d, "younger ecosystem: fewer libraries and hires")


def scale_fit(c, p):
    t = c.t
    if t["users_max"] and p.users > t["users_max"]:
        r = p.users / t["users_max"]
        c.add("scale.users_12_months", -min(4.0, 1.5 + math.log2(r)),
              f"designed for up to ~{t['users_max']:,} users; target is {p.users:,}")
    if t["users_min"] and p.users < t["users_min"]:
        r = t["users_min"] / max(p.users, 1)
        c.add("scale.users_12_months", -min(4.0, 1.5 + math.log10(r)),
              f"over-engineering for {p.users:,} users (pays off beyond ~{t['users_min']:,})", kind="overeng")


def lock_fit(c, p):
    pen = {"high": {"low": -2.2, "medium": -0.6, "high": 0.0},
           "medium": {"low": -0.8, "medium": -0.15, "high": 0.0}}.get(c.t["lock"], {}).get(p.lock_tolerance, 0.0)
    if pen:
        c.add("infrastructure.vendor_lock_in_tolerance", pen,
              f"{c.t['lock']} vendor lock-in (proprietary APIs/data model) with lock-in tolerance '{p.lock_tolerance}'")


def existing_fit(c, p, bonus=3.0):
    from .kb.lifecycle import LIFECYCLE
    for sysname in p.existing:
        low = sysname.lower()
        for pat in c.t["aliases"]:
            if re.search(pat, low):
                eol = any(re.search(lp, low) for item in LIFECYCLE if item["kind"] in ("eol", "maintenance", "closed")
                          for lp in item["patterns"])
                if eol:
                    c.add("infrastructure.existing_systems", bonus * 0.6,
                          f"continues the team's existing '{sysname}' technology on a supported version")
                else:
                    c.add("infrastructure.existing_systems", bonus, f"reuses the existing '{sysname}'")
                return True
    return False


def budget_fit(c, p, lo, share, label):
    """Penalise components whose own floor cost eats more than their share of the budget."""
    cap = max(p.budget * share, 3.0)
    if lo > cap and lo > 5:
        d = -min(3.5, 1.1 * math.log2(lo / cap) + 0.3)
        c.add("budget.monthly_infra_usd", d,
              f"{label} starts around ${lo:,.0f}/month against a ${p.budget:,.0f}/month total budget")
    elif lo == 0 and p.budget <= 20:
        c.add("budget.monthly_infra_usd", 0.8, f"free tier fits budget.monthly_infra_usd={p.budget:,.0f}")


def common(c, p, *, skills=1.0, ops=1.0, prio=0.55, learn=True, mature=True, dimw=None):
    priority_fit(c, p, weight=prio, dimw=dimw)
    if skills:
        skill_fit(c, p, weight=skills)
    if learn:
        learning_fit(c, p)
    if ops:
        ops_fit(c, p, weight=ops)
    if mature:
        maturity_fit(c, p)
    scale_fit(c, p)
    lock_fit(c, p)
