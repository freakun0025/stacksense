"""Selection logic for the four core layers (frontend, backend, database, hosting) + managed DB offering."""
import math

from .kb import layer, BY_ID, REGION_NAMES
from .scoring import (Cand, rank, hard_exclusion, common, skill_fit, existing_fit, budget_fit, ops_fit,
                      HYPERSCALERS, CLOUD_LABEL)

PLAT_LABEL = {"android": "Android", "ios": "iOS"}
# Client frameworks scale through CDNs/app stores, so their 'scalability' score matters less.
FE_DIMW = {"scalability": 0.3, "security": 0.6}
TEMPLATE_BACKENDS = ("django", "rails", "laravel", "spring_boot", "aspnet_core", "phoenix", "go_chi", "fastapi")


class LayerResult:
    def __init__(self, name):
        self.name = name
        self.winner = None
        self.ranked = []
        self.excluded = []
        self.none_reason = None
        self.none_fields = []
        self.none_alternatives = []
        self.parts = []           # frontend: [(part, Cand, ranked, excluded, plats)]
        self.label = None
        self.family = None        # hosting provider family
        self.region_name = None
        self.mode = None

    @property
    def is_none(self):
        return self.winner is None and not self.parts


def evaluate(techs, p, fn, ctx=None, pii=None):
    cands = []
    for t in techs:
        c = Cand(t)
        ex = hard_exclusion(t, p, pii=pii)
        if ex:
            c.excluded = ex
        else:
            fn(c, p, ctx or {})
        cands.append(c)
    return rank(cands)


def _plat_label(plats):
    return " + ".join(PLAT_LABEL[x] for x in plats)


# ================================================================== FRONTEND
def _mobile_factors(c, p, ctx):
    t, tr = c.t, c.t["traits"]
    need = ctx["need"]
    if not set(need) <= set(t["plats"]):
        missing = [x for x in need if x not in t["plats"]]
        c.excluded = (f"does not target {', '.join(missing)} (project.platforms)", ["project.platforms"])
        return
    if "game" in tr and p.type != "gaming":
        c.excluded = ("game engine: only for project.type=gaming", ["project.type"])
        return
    common(c, p, dimw=FE_DIMW)
    if len(need) == 2 and "cross_platform" in tr:
        c.add("project.platforms", 1.4, "one codebase ships both Android and iOS (project.platforms)")
    if p.type == "gaming":
        c.add("project.type", 4.0 if "game" in tr else -2.0,
              "game engine with rendering/physics loop for project.type=gaming" if "game" in tr
              else "not a game engine (project.type=gaming)")
    if p.offline:
        if "offline_capable" in tr:
            c.add("requirements.offline_support", 1.0, "on-device SQLite storage and background sync for offline_support=true")
        elif "no_store" in tr:
            c.add("requirements.offline_support", -2.0, "PWA storage can be evicted and background sync is limited (offline_support=true)")
        else:
            c.add("requirements.offline_support", -0.6, "WebView storage is a weaker base for offline-first data")
    if p.low_end:
        if "low_end_ok" in tr:
            c.add("project.description", 1.0, "compiled runtime keeps memory low on the low-end devices in the description")
        elif "web_reuse" in tr:
            c.add("project.description", -0.8, "WebView apps struggle on the low-end devices in the description")
        elif t["id"] == "expo_rn":
            c.add("project.description", -0.3, "JS runtime adds memory overhead on low-end devices (Hermes mitigates)")
    if p.poor_network and "offline_capable" in tr:
        c.add("project.description", 0.3, "queues uploads locally for the intermittent networks described")
    if p.prio["performance"] >= 4 and "native" in tr:
        c.add("priorities.performance", 0.4, "native rendering for performance priority")


def _web_factors(c, p, ctx):
    t, tr = c.t, c.t["traits"]
    if "game" in tr and p.type != "gaming":
        c.excluded = ("game framework: only for project.type=gaming", ["project.type"])
        return
    if "needs_server" in tr and not p.needs_backend:
        c.excluded = ("server-rendered templates need a running backend; this site is static", ["project.type"])
        return
    common(c, p, dimw=FE_DIMW)
    content = p.type == "content_site" or p.static_eligible
    if "server_templates" in tr:
        if p.type in ("realtime_collab", "data_analytics", "gaming", "iot", "saas_b2b", "social"):
            c.add("project.type", -1.2, f"a highly interactive {p.type} UI is better served by a client-side framework")
        elif p.type in ("internal_tool", "web_app") or (p.team_size <= 2 and p.exp == "beginner"):
            c.add("project.type", 0.6, "form-heavy CRUD screens render well on the server")
        if p.offline:
            c.add("requirements.offline_support", -1.5, "server-rendered pages do not work offline")
        if p.mobile:
            c.add("project.platforms", -0.8, "mobile apps need a JSON API anyway; a JS client can reuse it")
    if p.seo:
        if "ssr" in tr or "ssg" in tr:
            c.add("requirements.seo_critical", 1.6, "server-rendered/pre-rendered HTML for seo_critical=true")
        else:
            c.add("requirements.seo_critical", -2.5, "client-only rendering hurts crawlability (seo_critical=true)")
    if content:
        if "static_first" in tr:
            c.add("project.type", 1.8, f"static-first output for a {p.type} (scale.workload={p.workload})")
        elif "ssg" in tr:
            c.add("project.type", 0.5, "can pre-render pages at build time")
        if "markdown_content" in p.signals and "content" in tr:
            c.add("project.description", 0.6, "Markdown content collections match the Markdown authoring in the description")
        if "rich_ui" in tr and "ssr" not in tr:
            c.add("project.type", -0.6, "heavy client-side framework for mostly static pages")
    else:
        if "static_first" in tr and "islands" not in tr:
            c.excluded = (f"static site generator cannot serve an interactive {p.type}", ["project.type"])
            return
        if "islands" in tr:
            c.add("project.type", -1.6, f"islands model is awkward for an app-like {p.type}")
        if p.type in ("realtime_collab", "saas_b2b", "internal_tool", "data_analytics", "web_app", "fintech",
                      "healthtech", "marketplace", "ecommerce", "social", "ai_ml_product"):
            if "rich_ui" in tr or "spa" in tr:
                c.add("project.type", 0.8, f"rich client-side interactivity for a {p.type}")
        if p.type == "realtime_collab" and "react" in tr:
            c.add("project.type", 1.0, "React ecosystem has mature canvas (tldraw, Excalidraw) and Yjs CRDT bindings for collaborative editing")
    if p.type == "gaming":
        c.add("project.type", 4.0 if "game" in tr else -2.0,
              "browser game framework" if "game" in tr else "not a game framework (project.type=gaming)")
    if p.offline and "pwa" in tr:
        c.add("requirements.offline_support", 0.5, "service-worker/PWA support for offline_support=true")
    mob = ctx.get("mobile")
    if mob is not None and "react" in tr and "react" in mob.t["traits"]:
        c.add("project.platforms", 1.0, f"shares React/TypeScript skills and code with the {mob.t['name']} app")
    if "csharp_web" in tr:
        if any(k in " ".join(p.existing).lower() for k in ("entra", "azure ad", "microsoft 365", "office 365")):
            c.add("infrastructure.existing_systems", 0.6, "integrates natively with the existing Microsoft identity/estate")
    if p.type == "internal_tool" and "enterprise" in tr:
        c.add("project.type", 0.3, "structured framework suits form-heavy internal tooling")
    if p.type == "internal_tool" and p.seo is False and "static_first" in tr:
        c.add("project.type", -1.0, "internal tools gain nothing from static-first SEO output")


def _desktop_factors(c, p, ctx):
    common(c, p)
    web = ctx.get("web")
    if web is not None and "web_reuse" in c.t["traits"]:
        c.add("project.platforms", 0.8, f"reuses the {web.t['name']} web UI code on the desktop")
    mob = ctx.get("mobile")
    if mob is not None and mob.t["langs"] and c.t["langs"] and mob.t["langs"][0] == c.t["langs"][0]:
        c.add("project.platforms", 0.6, f"same language as the {mob.t['name']} mobile app")


def select_frontend(p):
    r = LayerResult("frontend")
    if p.api_only:
        r.none_reason = ("project.platforms=['api_only']: there is no end-user UI to build; API consumers integrate "
                         "via the published OpenAPI contract")
        r.none_fields = ["project.platforms"]
        return r
    mob = web = None
    if p.mobile:
        need = [x for x in ("android", "ios") if x in p.platforms]
        ok, ex = evaluate(layer("mobile"), p, _mobile_factors, {"need": need})
        if ok:
            mob = ok[0]
            r.parts.append(("mobile", mob, ok, ex, need))
    if p.web:
        ok, ex = evaluate(layer("web"), p, _web_factors, {"mobile": mob})
        if ok:
            web = ok[0]
            r.parts.insert(0, ("web", web, ok, ex, ["web"]))
    if p.desktop:
        ok, ex = evaluate(layer("desktop"), p, _desktop_factors, {"web": web, "mobile": mob})
        if ok:
            r.parts.append(("desktop", ok[0], ok, ex, ["desktop"]))
    labels = []
    for part, cand, _, _, plats in r.parts:
        if part == "web":
            labels.append(cand.label + (" (web)" if len(r.parts) > 1 else ""))
        elif part == "mobile":
            labels.append(f"{cand.label} for {_plat_label(plats)}")
        else:
            labels.append(f"{cand.label} (desktop)")
    r.label = " + ".join(labels)
    r.winner = r.parts[0][1] if r.parts else None
    return r


# ================================================================== BACKEND
def _backend_factors(c, p, ctx):
    t, tr = c.t, c.t["traits"]
    web = ctx.get("web")
    common(c, p, skills=1.0)
    existing_fit(c, p)
    if "functions" in tr:
        if p.realtime:
            c.add("requirements.realtime", -3.0, "functions cannot hold the persistent connections realtime=true needs")
        if p.offline or p.files:
            c.add("requirements.offline_support" if p.offline else "requirements.file_media_storage", -0.8,
                  "sync batches and large uploads run into function time/size limits")
        if p.complex_domain:
            c.add("project.type", -1.5, f"a {p.type} domain needs a structured service, not scattered functions")
        elif p.tier_i <= 1:
            c.add("scale.users_12_months", 0.8, "low, bursty load suits pay-per-request functions")
    if "baas" in tr:
        if p.complex_domain:
            c.add("project.type", -1.2 - (0.8 if p.team_size >= 5 else 0),
                  f"complex {p.type} workflows outgrow BaaS rules and edge functions")
        else:
            c.add("project.type", 1.2, "BaaS covers auth, data and storage without writing server code")
        if p.team_size <= 3 and p.prio["time_to_market"] >= 4:
            c.add("priorities.time_to_market", 0.8, f"{p.team_size}-person team with time_to_market={p.prio['time_to_market']}")
        if p.team_size >= 6:
            c.add("team.size", -0.8, f"a {p.team_size}-engineer team benefits from owning a proper service layer")
        if p.auth in ("phone_otp", "social", "email_password") and "auth" in tr:
            c.add("requirements.auth", 0.5, f"built-in {p.auth} authentication")
        if p.files and "storage" in tr:
            c.add("requirements.file_media_storage", 0.3, "built-in file storage")
        if p.offline and "offline_sync" in tr:
            c.add("requirements.offline_support", 1.2, "SDK-level offline persistence and sync")
        if p.ml != "none":
            c.add("requirements.ml_features", -0.5, "ML serving needs a separate service anyway")
        if "auth_global" in tr and p.effective_residency != "none" and p.auth != "none":
            c.excluded = ("its Authentication product has no data-location choice (infrastructure.data_residency)",
                          ["infrastructure.data_residency"])
            return
        if "single_node" in tr and p.ha >= 2:
            c.add("requirements.availability", -2.5, f"single-node design cannot meet availability {p.availability}%")
    if p.realtime:
        if "realtime_strong" in tr:
            c.add("requirements.realtime", 1.2, "lightweight concurrency for many persistent WebSocket connections")
            if p.type == "realtime_collab" and p.peak_cc >= 1000:
                c.add("scale.peak_concurrent_users", 0.6, f"{p.peak_cc:,} concurrent editors at peak")
        elif "realtime_ok" in tr:
            c.add("requirements.realtime", 0.5, "first-class WebSocket support for realtime=true")
        elif "no_websockets" in tr:
            c.add("requirements.realtime", -2.5, "no persistent WebSocket support on its usual hosts")
    if p.complex_domain or p.audit or p.multi_tenant:
        if "structured" in tr:
            c.add("project.type", 0.8, f"modules/DI give structure for a {p.type} domain")
        elif "minimal" in tr:
            c.add("project.type", -0.3, "minimal framework leaves domain structure to the team")
    if p.ledger and "acid_strong" in tr:
        c.add("project.description", 0.8, "declarative ACID transactions for the double-entry ledger in the description")
    if p.ml != "none" and "python_ml" in tr:
        c.add("requirements.ml_features", 0.8, f"Python ML ecosystem for ml_features={p.ml}")
    if p.p95 and p.p95 <= 150:
        d = (t["scores"]["performance"] - 3) * 0.45
        if d:
            c.add("requirements.p95_latency_ms", d, f"runtime latency headroom for a {p.p95} ms p95 target")
    if "entra_native" in tr and p.auth == "enterprise_sso":
        ms = any(k in " ".join(p.existing).lower() for k in ("entra", "azure ad", "active directory", "microsoft 365"))
        if ms or p.cloud == "azure":
            c.add("infrastructure.existing_systems" if ms else "infrastructure.cloud_preference", 1.2,
                  "Microsoft.Identity.Web makes Entra ID SSO a configuration task")
    if "fullstack" in tr:
        if web is None or web.id != "nextjs":
            c.excluded = ("only applies when the web frontend is Next.js", ["project.platforms"])
            return
        c.add("project.platforms", 1.0, "same Next.js codebase and deploy as the web frontend")
        if p.complex_domain:
            c.add("project.type", -1.0, "domain logic would be tangled with UI code")
        if p.mobile:
            c.add("project.platforms", -0.6, "mobile clients need a stable versioned API separate from the web app")
    if web is not None and web.id == "htmx":
        if "baas" in tr or "functions" in tr or "fullstack" in tr:
            c.excluded = ("server-rendered HTMX templates need a server framework", ["frontend"])
            return
        if t["id"] in TEMPLATE_BACKENDS:
            c.add("frontend", 1.0, "renders the HTMX templates with its built-in template engine")
        else:
            c.add("frontend", -0.5, "template rendering is not this framework's strength")
    clients = ctx.get("client_langs") or set()
    if t["langs"] and clients and "baas" not in tr and set(t["langs"]) & clients:
        c.add("project.platforms", 0.6, "same language as the web/mobile clients: shared types and validation code")
    if t["id"] == "supabase" and p.region == "india":
        c.add("infrastructure.data_residency", -0.8, "supabase.co was ISP-blocked in India in Feb 2026; needs a custom domain")
    if "low_memory" in tr and p.prio["cost"] >= 4:
        c.add("priorities.cost", 0.3, "small memory footprint keeps instance costs low")
    if p.restricted and "baas" in tr:
        c.add("infrastructure.deployment_model", -2.0, "self-hosting a full BaaS stack on-premise is operationally heavy")
    if p.type == "gaming" and "realtime_strong" in tr:
        c.add("project.type", 0.6, "efficient game-session networking")


def select_backend(p, frontend):
    r = LayerResult("backend")
    web = next((cand for part, cand, *_ in frontend.parts if part == "web"), None)
    if not p.needs_backend:
        if p.forms:
            ok, ex = evaluate([BY_ID["functions"]], p, lambda c, p_, ctx: c.add(
                "project.description", 2.0, "the description mentions forms/registration: one small function handles submissions"))
            if ok:
                r.winner, r.ranked, r.excluded = ok[0], ok, ex
                r.label = "Serverless function (form handler)"
                return r
        r.none_reason = (f"No dynamic requirement: project.type={p.type}, auth=none, payments/realtime/uploads/ML all false, "
                         f"workload={p.workload}. Pages are generated at build time, so there is no server to run.")
        r.none_fields = ["project.type", "requirements.auth", "scale.workload", "requirements.payments"]
        r.none_alternatives = [{"choice": "Serverless functions",
                                "why_not": "nothing to execute per request; would add cost and attack surface for no benefit"}]
        return r
    client_langs = set()
    for part, cand, *_ in frontend.parts:
        client_langs |= set(cand.t["langs"][:2])
    ok, ex = evaluate(layer("backend"), p, _backend_factors, {"web": web, "client_langs": client_langs})
    r.ranked, r.excluded = ok, ex
    if ok:
        r.winner = ok[0]
        r.label = ok[0].label
    return r


# ================================================================== DATABASE ENGINE
RELATIONAL_TYPES = ("fintech", "ecommerce", "marketplace", "healthtech", "saas_b2b", "internal_tool")


def _db_factors(c, p, ctx):
    t, tr = c.t, c.t["traits"]
    common(c, p, skills=0.0, ops=0.0, learn=False)
    existing_fit(c, p, bonus=2.5)
    rel_need = p.complex_domain or p.payments or p.ledger or p.multi_tenant or p.audit or p.type in RELATIONAL_TYPES
    if "olap" in tr:
        if p.type != "data_analytics":
            c.excluded = ("analytical (OLAP) store, not a transactional database", ["project.type"])
            return
        if p.data_gb >= 500:
            c.add("scale.data_volume_gb_12_months", 2.5, f"columnar engine for {p.data_gb:,.0f} GB of analytical data")
        else:
            c.add("scale.data_volume_gb_12_months", -0.8, f"{p.data_gb:,.0f} GB fits comfortably in PostgreSQL")
    if rel_need:
        if "acid" in tr or "relational" in tr:
            c.add("project.type", 1.5, f"relational integrity and transactions for a {p.type} domain")
        elif "olap" not in tr:
            c.add("project.type", -2.0 if (p.ledger or p.type == "fintech") else -1.0,
                  "money/relational data needs multi-row ACID guarantees")
    if p.ledger and "acid" in tr:
        c.add("project.description", 1.0, "strict ACID + constraints for the double-entry ledger")
    if p.fts and ("fts" in tr or "fts_atlas" in tr):
        c.add("requirements.full_text_search", 0.4, "built-in full-text search covers full_text_search=true at this scale")
    if p.geospatial and "geo" in tr:
        c.add("project.description" if p.data.get("requirements", {}).get("geospatial") is None else "requirements.geospatial",
              0.8, "geospatial indexing for the GPS/location data")
    if p.multi_tenant and "rls" in tr:
        c.add("requirements.multi_tenant", 0.5, "row-level security policies isolate tenants")
    if p.ml == "llm_rag" and "vector" in tr:
        c.add("requirements.ml_features", 0.5, "stores embeddings next to the data (vector search)")
    if p.workload == "write_heavy" and p.tier_i >= 3 and "write_scale" in tr:
        c.add("scale.workload", 1.5, f"write-heavy load at {p.tier} scale")
    if p.type == "iot":
        if "timeseries" in tr:
            c.add("project.type", 2.0, "time-series hypertables for device telemetry")
    if "embedded" in tr:
        if p.tier_i == 0 and p.ha == 0 and p.team_size <= 2:
            c.add("scale.users_12_months", 0.5, "tiny single-server workload")
        else:
            c.add("requirements.availability", -2.0, "single embedded file cannot serve multiple instances or HA")
    if "sql" in p.langs and "relational" in tr:
        c.add("team.languages", 0.4, "team lists SQL")
    if t["id"] == "sqlserver":
        if p.cloud == "azure" and any(l in p.langs for l in ("csharp", "fsharp")):
            c.add("infrastructure.cloud_preference", 0.8, "Azure SQL + Entity Framework is the default .NET-on-Azure pairing")
        elif p.cloud != "azure":
            c.add("priorities.cost", -0.8, "SQL Server licensing outside Azure SQL's managed tiers")
    if t["id"] == "firestore" and ctx.get("backend_id") != "firebase":
        c.add("backend", -2.0, "Firestore's offline/realtime strengths need the Firebase client SDK and Firebase Auth")
    elif p.offline and p.mobile and "offline_sync" in tr:
        c.add("requirements.offline_support", 0.6, "client SDKs sync offline writes")
    if p.realtime and "realtime" in tr:
        c.add("requirements.realtime", 0.3, "change streams to clients")
    if p.ha == 3 and "multi_region" in tr:
        c.add("requirements.availability", 1.0, "multi-region replication for 99.99%")
    if t["provider"] in HYPERSCALERS and p.cloud in HYPERSCALERS and t["provider"] == p.cloud:
        c.add("infrastructure.cloud_preference", 0.3, f"native {CLOUD_LABEL[p.cloud]} service")
    if "document" in tr and not rel_need and p.prio["time_to_market"] >= 4:
        c.add("priorities.time_to_market", 0.3, "schema-flexible documents speed early iteration")


def select_database(p, backend):
    r = LayerResult("database")
    if backend.is_none or (backend.winner and backend.winner.id == "functions" and not p.needs_backend):
        r.none_reason = ("No persistent application data: content is authored as files in the repository and "
                         "compiled at build time" + (" (Markdown, per project.description)" if "markdown_content" in p.signals else ""))
        r.none_fields = ["project.type", "requirements.auth", "project.description"]
        r.none_alternatives = [{"choice": "Headless CMS / SQLite",
                                "why_not": "adds a moving part and cost for content a single author edits as files"}]
        return r
    forced = None
    if backend.winner and backend.winner.id == "supabase":
        forced = "postgresql"
    elif backend.winner and backend.winner.id == "firebase":
        forced = "firestore"

    def fn(c, p_, ctx):
        _db_factors(c, p_, ctx)
        if forced and not c.excluded:
            if c.id == forced:
                c.add("backend", 6.0, f"{backend.winner.t['name'].split(' (')[0]} is built on {c.t['name']}")
            else:
                c.add("backend", -6.0, f"would bypass the {backend.winner.t['name'].split(' (')[0]} data model")
    ok, ex = evaluate(layer("database"), p, fn, {"backend_id": backend.winner.id if backend.winner else None}, pii=True)
    # engines are software: residency/compliance is enforced on the offering, so don't exclude here
    r.ranked, r.excluded = ok, ex
    r.winner = ok[0] if ok else None
    return r


# ================================================================== HOSTING
K8S_LABEL = {"aws": "Amazon EKS", "gcp": "GKE Autopilot", "azure": "Azure Kubernetes Service (AKS)"}
VM_LABEL = {"aws": "Docker Compose on Amazon EC2", "gcp": "Docker Compose on Compute Engine VMs",
            "azure": "Docker Compose on Azure VMs"}


def hosting_family(t, p):
    if t["id"] == "kubernetes":
        return p.cloud if p.cloud in HYPERSCALERS else "gcp"
    if t["id"] == "vm_compose":
        return p.cloud if p.cloud in HYPERSCALERS else "vm"
    if t["id"] in ("onprem_compose", "onprem_k8s"):
        return "self"
    return t["provider"]


def hosting_label(c, p, mode):
    t = c.t
    fam = hosting_family(t, p)
    name = t["name"]
    if t["id"] == "kubernetes":
        name = K8S_LABEL.get(fam, name)
    elif t["id"] == "vm_compose":
        name = VM_LABEL.get(fam, "Docker Compose on cloud VMs (e.g. DigitalOcean Droplets, EC2)")
    if mode == "static" and "static" in t["traits"]:
        return f"{name} (global CDN)", None
    names = REGION_NAMES.get(fam, {}) or t["region_names"]
    region = names.get(p.region) if p.region in names else None
    if fam == "self":
        region = REGION_NAMES["self"].get(p.effective_residency if p.effective_residency != "none" else "none")
    return (f"{name} ({region})" if region else name), region


def _hosting_factors(c, p, ctx):
    t, tr = c.t, c.t["traits"]
    mode = ctx["mode"]
    be = ctx.get("backend")
    fe_web = ctx.get("web")
    common(c, p, skills=0.0, ops=1.2, prio=0.5)
    existing_fit(c, p, bonus=1.0)
    lo = t["cost"][p.tier_i][0]
    budget_fit(c, p, lo, 0.5, t["name"])
    if t["id"] == "gamelift" and p.type != "gaming":
        c.excluded = ("dedicated game-server fleets: only for project.type=gaming", ["project.type"])
        return
    if mode == "static":
        if "static" in tr:
            c.add("project.type", 2.5, "serves pre-built static files from a global CDN")
            if "containers" in tr:
                c.add("project.type", -1.0, "general-purpose app platform; static hosting is a side feature")
            if "git_deploy" in tr:
                c.add("team.experience", 0.4, "push-to-deploy from Git with no pipeline to maintain")
            if p.forms and "functions" in tr:
                c.add("project.description", 0.6, "runs the small form-handler function next to the static site")
            if p.forms and "forms" in tr:
                c.add("project.description", 0.6, "built-in form handling")
        else:
            c.add("project.type", -2.0, "runs servers a static site does not need")
        if t["id"] == "github_pages" and p.budget == 0:
            c.add("budget.monthly_infra_usd", 0.3, "free for public repositories")
        return
    # dynamic modes
    if mode == "frontend":
        # backend is a BaaS; this platform only serves the web frontend
        if "static" not in tr and "ssr_native" not in tr and "ssr_ok" not in tr:
            c.add("backend", -0.8, f"container platform is unnecessary when {be.t['name'].split(' (')[0]} is the backend")
        else:
            c.add("backend", 1.0, "serves the web frontend; the BaaS handles data and auth")
    else:
        bt = be.t if be else None
        long_running = bt is not None and "functions" not in bt["traits"] and "fullstack" not in bt["traits"]
        if long_running and "containers" not in tr:
            c.excluded = (f"cannot run a long-lived {bt['name']} server process", ["backend"])
            return
        if bt is not None and ("functions" in bt["traits"] or "fullstack" in bt["traits"]):
            if "functions" in tr or "ssr_native" in tr:
                c.add("backend", 1.0, "native support for serverless functions/route handlers")
        if "containers" in tr:
            c.add("backend", 0.5, f"runs the {bt['name'] if bt else 'backend'} container as-is")
        if p.realtime and long_running:
            if "websockets" not in tr or "no_websockets" in tr:
                c.add("requirements.realtime", -3.0, "cannot keep WebSocket connections open (realtime=true)")
        if bt is not None and "entra_native" in bt["traits"] and "dotnet_native" in tr:
            c.add("backend", 1.0, ".NET-native hosting with deployment slots and built-in Entra auth")
    if fe_web is not None and fe_web.id == "nextjs":
        if "ssr_native" in tr:
            c.add("frontend", 1.2, "native Next.js SSR/ISR hosting")
        elif "ssr_ok" in tr:
            c.add("frontend", 0.4, "supports Next.js SSR")
    if p.traffic in ("spiky", "seasonal"):
        if "autoscale" in tr:
            c.add("scale.traffic_pattern", 0.8, f"autoscaling absorbs {p.traffic} traffic")
        if "scale_to_zero" in tr and p.prio["cost"] >= 3:
            c.add("scale.traffic_pattern", 0.4, "scales to zero between bursts")
        if "vm" in tr:
            c.add("scale.traffic_pattern", -0.8, f"fixed VMs must be sized for {p.traffic} peaks")
    if p.ha >= 2:
        if "multi_az" in tr:
            c.add("requirements.availability", 1.0, f"multi-zone redundancy for availability {p.availability}%")
        elif "vm" in tr:
            c.add("requirements.availability", -2.5, f"single VMs cannot reach {p.availability}% without a hand-built HA setup")
        else:
            c.add("requirements.availability", -0.6, f"limited multi-zone guarantees for {p.availability}%")
    if p.realtime and p.type in ("realtime_collab", "gaming") and mode == "app" and "containers" in tr:
        if "sticky" in tr:
            c.add("project.type", 0.8, "sticky routing keeps every client of a board/room on the same stateful server")
        else:
            c.add("project.type", -1.0, "only best-effort session affinity for stateful rooms")
    if p.type == "gaming" and p.realtime:
        if "udp" not in tr:
            c.add("project.type", -2.5, "game netcode needs UDP; HTTP-only platforms cannot host game servers")
        if "game_servers" in tr:
            c.add("project.type", 3.0, "managed dedicated game-server fleets and matchmaking")
    if "hybrid_connectivity" in tr and any(("on-prem" in s.lower() or "on prem" in s.lower()) for s in p.existing):
        c.add("infrastructure.existing_systems", 0.8, "Hybrid Connections reach the existing on-prem systems without a VPN")
    if "k8s" in tr and p.team_size >= 15 and p.has_devops:
        c.add("team.size", 1.0, f"{p.team_size} engineers with DevOps can run a shared platform")
    if p.p95 and p.p95 <= 100 and "global_edge" in tr and p.geography and len(p.geography) > 1:
        c.add("scale.user_geography", 0.8, "runs close to globally distributed users")
    for lic, prov in (("aws", "aws"), ("gcp", "gcp"), ("azure", "azure"), ("microsoft", "azure")):
        if any(lic in l for l in p.licences) and hosting_family(t, p) == prov:
            c.add("infrastructure.existing_licences", 1.0, f"uses existing {CLOUD_LABEL[prov]} credits/licences")
            break
    if "k8s" in tr and not p.has_devops and p.team_size < 6:
        c.add("team.has_devops", -2.5, f"Kubernetes needs a platform team; {p.team_size} engineer(s) without DevOps")
    if p.restricted and "k8s" in tr and p.has_devops:
        if p.tier_i >= 3 or p.ha >= 2:
            c.add("requirements.availability", 1.0, "self-healing multi-node cluster for on-prem availability")


def select_hosting(p, frontend, backend):
    r = LayerResult("hosting")
    web = next((cand for part, cand, *_ in frontend.parts if part == "web"), None)
    be = backend.winner
    if be is None or (be.id == "functions" and not p.needs_backend):
        mode = "static"
    elif "baas" in be.t["traits"]:
        mode = "frontend"
    else:
        mode = "app"
    r.mode = mode
    if mode == "frontend" and web is None:
        # mobile-only on a BaaS: the BaaS itself is the hosting platform
        c = Cand(be.t)
        c.add("backend", 3.0, "mobile clients talk directly to the managed BaaS; there is no web tier to host")
        fam = be.t["provider"]
        region = (be.t["region_names"] or REGION_NAMES.get(fam, {})).get(p.region)
        r.winner, r.ranked = c, [c]
        r.family = fam
        r.region_name = region
        r.label = f"{be.t['name'].split(' (')[0]} managed platform" + (f" ({region})" if region else "")
        ok, ex = evaluate(layer("hosting"), p, _hosting_factors, {"mode": "app", "backend": None, "web": None}, pii=True)
        r.excluded = ex
        r.ranked = [c] + ok[:3]
        return r
    pii = mode == "app" or (p.auth != "none" and web is not None and web.id in ("nextjs", "nuxt", "sveltekit", "blazor"))
    ok, ex = evaluate(layer("hosting"), p, _hosting_factors, {"mode": mode, "backend": be, "web": web}, pii=pii)
    r.ranked, r.excluded = ok, ex
    if ok:
        r.winner = ok[0]
        r.label, r.region_name = hosting_label(ok[0], p, mode)
        r.family = hosting_family(ok[0].t, p)
    return r


# ================================================================== DATABASE OFFERING
def _offering_factors(c, p, ctx):
    t, tr = c.t, c.t["traits"]
    fam = ctx["family"]
    be = ctx.get("backend")
    if t["id"] == "sqlite_embedded" and fam not in ("vm", "self", "fly", "render", "railway"):
        c.excluded = ("needs a persistent local disk; the chosen hosting runs ephemeral containers", ["hosting"])
        return
    ops_fit(c, p, weight=1.0)
    existing_fit(c, p, bonus=1.5)
    mult = ha_multiplier(t, p)
    lo = t["cost"][p.tier_i][0] * mult
    budget_fit(c, p, lo, 0.35, t["name"])
    d = -0.35 * (p.prio["cost"] / 3.0) * math.log2(1 + lo / 10.0)
    if d:
        c.add("priorities.cost", d, f"~${lo:,.0f}+/month at the {p.tier} tier")
    if fam and t["provider"] == fam:
        c.add("hosting", 3.0, "same platform and private network as the application hosting")
    elif fam in HYPERSCALERS and t["provider"] in HYPERSCALERS:
        c.add("hosting", -2.0, "different cloud from the application: cross-cloud latency and egress")
    elif fam in ("vercel", "netlify", "cloudflare", "github") and t["provider"] in ("neon", "supabase", "mongodb"):
        c.add("hosting", 0.8, "serverless-friendly connection model for function hosts")
    elif fam not in HYPERSCALERS and fam not in ("self", "vm") and t["provider"] in HYPERSCALERS:
        c.add("hosting", -1.5, f"adds a hyperscaler account next to {fam} hosting")
    if be is not None and be.id == "supabase":
        c.add("backend", 6.0 if t["id"] == "supabase_pg" else -6.0,
              "the Supabase project's own Postgres" if t["id"] == "supabase_pg" else "Supabase already includes Postgres")
    if p.ha >= 2 and not ({"ha", "serverless", "ha_builtin", "serverless_tier"} & set(tr)):
        c.add("requirements.availability", -2.0, f"no managed standby/failover for availability {p.availability}%")
    if p.ha >= 1 and ({"ha", "serverless_tier"} & set(tr)):
        c.add("requirements.availability", 0.4, "managed failover/standby available")
    if p.traffic in ("spiky", "seasonal") and "scale_to_zero" in tr and p.prio["cost"] >= 4:
        c.add("scale.traffic_pattern", 0.5, "storage-compute separation scales to zero between bursts")
    if p.rpo is not None and p.rpo < 5 and not ({"pitr", "ha"} & set(tr)):
        c.add("requirements.rpo_minutes", -1.5, f"cannot guarantee RPO < 5 min (rpo_minutes={p.rpo})")
    if p.ha == 3 and "multi_region" in tr:
        c.add("requirements.availability", 1.0, "cross-region replicas for 99.99%")


def ha_multiplier(t, p):
    tr = t["traits"]
    if p.ha == 0:
        return 1.0
    if {"serverless", "serverless_tier"} & set(tr):
        return 1.5 if p.ha == 3 else 1.0
    if "ha" in tr:
        if p.ha == 1 and p.prio["cost"] >= 4:
            return 1.0          # single-zone primary to respect cost priority (flagged as a warning)
        return {1: 1.6, 2: 2.0, 3: 3.0}[p.ha]
    return 1.0


def select_offering(p, engine_cand, hosting, backend):
    r = LayerResult("db_offering")
    if engine_cand is None:
        return r
    techs = [t for t in layer("db_offering") if t["kind"] == engine_cand.id]
    ok, ex = evaluate(techs, p, _offering_factors, {"family": hosting.family, "backend": backend.winner}, pii=True)
    r.ranked, r.excluded = ok, ex
    if ok:
        r.winner = ok[0]
        names = ok[0].t["region_names"] or REGION_NAMES.get(ok[0].t["provider"], {})
        if ok[0].t["provider"] == "self":
            r.region_name = REGION_NAMES["self"].get(p.effective_residency if p.effective_residency != "none" else "none")
        else:
            r.region_name = names.get(p.region)
    return r
