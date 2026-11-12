"""Supporting-service selection. Each needed capability is scored like a core layer."""
from .kb import layer, REGION_NAMES
from .scoring import (Cand, rank, hard_exclusion, priority_fit, ops_fit, lock_fit, scale_fit, existing_fit, budget_fit,
                      skill_fit, HYPERSCALERS)

OUT_LAYER = {"cache": "cache", "queue": "queue", "search": "search", "auth": "auth", "storage": "storage", "cdn": "cdn",
             "realtime": "realtime", "payments": "payments", "ml": "ml", "vector": "ml", "ml_training": "ml",
             "ci_cd": "ci_cd", "mobile_ci": "ci_cd", "observability": "observability"}
PURPOSE = {"sms": "SMS OTP delivery", "realtime_crdt": "collaborative editing (CRDT)", "vector": "vector search for RAG",
           "ml_training": "model training", "mobile_ci": "mobile build and release", "push": "push notifications",
           "email": "transactional notifications", "offline_sync": "on-device offline store and sync",
           "geospatial": "geospatial queries", "security": "security and compliance controls",
           "integration": "integration with existing on-prem systems", "iot": "device connectivity (MQTT)",
           "game_backend": "game server and matchmaking", "analytics": "reporting and BI"}
RELATIONAL = ("postgresql", "mysql", "sqlserver", "timescaledb", "cockroachdb")
PAAS_FAMILIES = ("supabase", "firebase", "vercel", "netlify", "cloudflare", "render", "railway", "fly", "digitalocean",
                 "github", "appwrite")
POSTGRES = ("postgresql", "timescaledb")

WS_VARIANT = {"nestjs": "Socket.IO gateways in NestJS", "fastify": "Socket.IO on Fastify", "express": "Socket.IO on Express",
              "go_chi": "Go WebSocket gateway (coder/websocket)", "aspnet_core": "ASP.NET Core SignalR",
              "django": "Django Channels (ASGI)", "fastapi": "FastAPI WebSockets", "spring_boot": "Spring WebSocket (STOMP)",
              "laravel": "Laravel Reverb", "rails": "Action Cable", "phoenix": "Phoenix Channels + Presence",
              "axum": "axum WebSockets (tokio)"}
PGQ_VARIANT = {"nestjs": "pg-boss", "fastify": "pg-boss", "express": "pg-boss", "nextjs_api": "pg-boss",
               "functions": "pg-boss", "django": "Procrastinate", "fastapi": "Procrastinate", "spring_boot": "JobRunr",
               "aspnet_core": "Hangfire", "go_chi": "River", "rails": "Solid Queue", "laravel": "Laravel database queue",
               "phoenix": "Oban", "axum": "apalis", "supabase": "Supabase Queues (pgmq) + pg_cron"}
REDISJ_VARIANT = {"nestjs": "BullMQ", "fastify": "BullMQ", "express": "BullMQ", "nextjs_api": "BullMQ", "django": "Celery",
                  "fastapi": "Celery", "rails": "Sidekiq", "laravel": "Laravel Horizon", "spring_boot": "Redis Streams consumers",
                  "aspnet_core": "Hangfire.Redis", "go_chi": "Asynq", "phoenix": "Exq", "axum": "apalis-redis"}
AUTH_VARIANT = {"nestjs": "Better Auth (NestJS)", "fastify": "Better Auth", "express": "Better Auth",
                "nextjs_api": "Better Auth", "django": "Django auth + django-allauth", "fastapi": "FastAPI Users",
                "spring_boot": "Spring Security (OAuth2/JWT)", "aspnet_core": "ASP.NET Core Identity",
                "go_chi": "Go sessions + goth OAuth", "laravel": "Laravel Fortify/Sanctum", "rails": "Rails 8 authentication",
                "phoenix": "phx.gen.auth", "axum": "axum-login", "functions": "Better Auth"}
OFFLINE_FOR = {"expo_rn": "watermelondb", "kotlin_android": "room_workmanager", "kmp": "room_workmanager",
               "flutter": "drift_sync", "capacitor": "watermelondb", "maui": None}
MOBILE_CI_FOR = {"expo_rn": "eas", "flutter": "codemagic"}


class SupportPick:
    def __init__(self, key, cand, ranked, excluded, label, region=None):
        self.key = key
        self.layer = OUT_LAYER.get(key, "other")
        self.purpose = PURPOSE.get(key)
        self.winner = cand
        self.ranked = ranked
        self.excluded = excluded
        self.label = label
        self.region = region


def _region_label(c, p, family):
    t = c.t
    prov = t["provider"]
    if not t["pii"] or "global_service" in t["traits"] or \
            prov in (None, "self", "host", "any", "cloud", "github", "expo", "codemagic"):
        return None
    names = REGION_NAMES.get(prov) or t["region_names"]
    return names.get(p.region) if names else None


def _base(c, p, ctx, key=None):
    t = c.t
    tr = t["traits"]
    eng = ctx["engine"]
    bid = ctx["backend_id"]
    if "requires_postgres" in tr and eng not in POSTGRES and not (c.id == "pg_queue" and eng in RELATIONAL):
        c.excluded = ("needs PostgreSQL as the primary database", ["database"])
        return False
    if c.id == "pg_queue" and eng not in RELATIONAL:
        c.excluded = ("needs a relational primary database", ["database"])
        return False
    if "requires_mongodb" in tr and eng != "mongodb":
        c.excluded = ("needs MongoDB as the primary database", ["database"])
        return False
    if "requires_supabase" in tr and bid != "supabase":
        c.excluded = ("only applies when Supabase is the backend", ["backend"])
        return False
    if "requires_firebase" in tr and bid != "firebase":
        c.excluded = ("only applies when Firebase is the backend", ["backend"])
        return False
    if "requires_cache" in tr and not ctx.get("cache"):
        c.excluded = ("no Redis/Valkey cache in this stack", ["supporting.cache"])
        return False
    if "requires_aspnet" in tr and bid != "aspnet_core":
        c.excluded = ("only for ASP.NET Core backends", ["backend"])
        return False
    if "static_only" in tr and not ctx["static"]:
        c.excluded = ("only for statically generated sites", ["project.type"])
        return False
    priority_fit(c, p, weight=0.35)
    ops_fit(c, p, weight=0.8)
    lock_fit(c, p)
    scale_fit(c, p)
    existing_fit(c, p, bonus=4.0)
    if t["langs"]:
        skill_fit(c, p, weight=0.5)
    lo = t["cost"][p.tier_i][0]
    budget_fit(c, p, lo, 0.15, t["name"])
    fam = ctx["family"]
    prov = t["provider"]
    if fam and prov == fam and prov not in ("self",):
        c.add("hosting", 1.0 if key == "auth" else 2.5, "same cloud/platform and region as the application")
    elif fam in HYPERSCALERS and prov in HYPERSCALERS and prov != fam:
        c.add("hosting", -2.0, "different cloud from the application hosting")
    elif fam not in HYPERSCALERS and fam not in ("self", "vm", None) and prov in HYPERSCALERS and t["pii"]:
        c.add("hosting", -1.5, f"adds a separate hyperscaler account next to the {fam} platform")
    if "requires_ms365" in tr and not any(k in " ".join(p.existing).lower() for k in
                                          ("microsoft 365", "office 365", "m365", "o365", "exchange online", "teams")):
        c.excluded = ("only when Microsoft 365 is an existing system", ["infrastructure.existing_systems"])
        return False
    if prov == "self" and t["ops"] >= 3 and not p.restricted and fam not in ("vm", "self"):
        c.add("infrastructure.deployment_model", -0.8, "self-hosting another service when a managed option exists")
    if p.restricted and prov == "self":
        c.add("infrastructure.deployment_model", 1.5, f"runs inside the {p.deployment.replace('_', '-')} network")
    return True


def _layer_fn(key):
    def fn(c, p, ctx):
        if not _base(c, p, ctx, key):
            return
        t, tr = c.t, c.t["traits"]
        bid, fam = ctx["backend_id"], ctx["family"]
        if key == "cache":
            if c.id == "valkey_self" and fam in ("vm", "self"):
                c.add("hosting", 2.5, "runs as another container next to the app")
            if c.id == "upstash" and fam in ("vercel", "netlify", "cloudflare"):
                c.add("hosting", 1.5, "HTTP API works from serverless/edge functions")
            if p.realtime:
                c.add("requirements.realtime", 0.3, "pub/sub backplane fans realtime messages out across instances")
        elif key == "queue":
            if c.id == "pg_queue":
                if p.tier_i <= 2:
                    c.add("scale.users_12_months", 2.2 if p.tier_i <= 1 else 1.2,
                          f"no extra infrastructure at {p.tier} scale; jobs commit with business data")
                    c.add("database", 1.0, "lives in the primary database already in the stack")
                else:
                    c.add("scale.users_12_months", -1.0, f"job volume at {p.tier} scale would load the primary database")
            if c.id == "redis_jobs" and ctx.get("cache"):
                c.add("supporting.cache", 0.6, "reuses the cache already in the stack")
            if p.payments and prov_in(t, HYPERSCALERS) and t["provider"] == fam:
                c.add("requirements.payments", 0.8, "dead-letter queues for payment webhooks and reconciliation")
            if c.id == "rabbitmq" and p.restricted:
                c.add("infrastructure.deployment_model", 1.0, "self-contained broker for restricted networks")
        elif key == "search":
            if c.id == "pagefind":
                c.add("project.type", 4.0, "index built at deploy time; zero runtime cost")
            if c.id == "pg_fts":
                if p.tier_i <= 2 and p.db_gb <= 500:
                    c.add("requirements.full_text_search", 2.0, f"Postgres FTS is enough for {p.db_gb:,.0f} GB at {p.tier} scale")
                else:
                    c.add("requirements.full_text_search", -1.5, "relevance/scale needs a dedicated engine")
            elif c.id not in ("pagefind", "atlas_search") and p.tier_i >= 3:
                c.add("requirements.full_text_search", 1.0, "dedicated engine for large-scale relevance tuning")
            if c.id == "atlas_search":
                c.add("requirements.full_text_search", 2.0, "search inside the same Atlas cluster")
        elif key == "auth":
            _auth_factors(c, p, ctx)
        elif key == "sms":
            if c.id == "msg91" and (p.effective_residency == "india" or p.region == "india"):
                c.add("infrastructure.data_residency", 2.0, "Indian DLT-registered SMS route; phone numbers processed in India")
            if c.id == "self_sms_modem":
                c.add("infrastructure.deployment_model", 1.0 if p.restricted else -3.0, "operator SMPP link")
            if c.id == "twilio_verify":
                c.add("project.platforms", 0.3, "global coverage")
        elif key == "storage":
            if p.poor_network and "resumable" in tr:
                c.add("project.description", 0.8, "resumable uploads survive the intermittent connectivity described")
            if "kyc" in p.signals and "sse_kms" in tr:
                c.add("project.description", 0.5, "KMS-encrypted private bucket for KYC documents")
            if "zero_egress" in tr and p.egress_gb > 1000:
                c.add("requirements.file_media_storage", 1.0, f"no egress fees on ~{p.egress_gb:,.0f} GB/month")
            if c.id == "supabase_storage":
                c.add("backend", 3.0, "same Supabase project and access policies")
        elif key == "cdn":
            if c.id == "host_cdn":
                if fam in ("vercel", "netlify", "cloudflare", "github") or ctx["static"]:
                    c.add("hosting", 4.0, "the hosting platform already serves through a global CDN")
                else:
                    c.excluded = ("the chosen hosting has no built-in CDN", ["hosting"])
                    return
            if c.id == "cloudflare_cdn" and p.prio["cost"] >= 3:
                c.add("priorities.cost", 0.8, "free plan covers unmetered CDN + DDoS protection")
            if p.effective_residency != "none":
                c.notes.append("cache only public, non-personal assets at the edge")
        elif key == "realtime":
            if c.id == "ws_native":
                if bid in WS_VARIANT:
                    c.add("requirements.realtime", 2.0, "messages stay inside your own backend and region")
                    if p.type in ("realtime_collab", "gaming") or p.peak_cc >= 5000:
                        c.add("scale.peak_concurrent_users", 0.8, f"full control of the hot path for {p.peak_cc:,} live connections")
                else:
                    c.excluded = ("the backend has no WebSocket server", ["backend"])
                    return
            if c.id in ("supabase_realtime", "firestore_rt"):
                c.add("backend", 3.0, "built into the BaaS already in the stack")
            if c.id == "azure_signalr" and fam == "azure":
                c.add("scale.peak_concurrent_users", 1.0 if p.peak_cc >= 1000 else -0.5,
                      "offloads connections from App Service" if p.peak_cc >= 1000 else "unneeded below ~1,000 connections")
            if c.id == "apigw_ws":
                if not (fam == "aws" and bid == "functions"):
                    c.excluded = ("only for Lambda-based backends on AWS", ["backend"])
                    return
            if c.id in ("ably", "pusher"):
                c.add("priorities.time_to_market", 0.4, "hosted channels with no server code")
                if p.type == "realtime_collab":
                    c.add("project.type", -1.0, "per-message pricing on a high-frequency cursor stream")
        elif key == "payments":
            _payment_factors(c, p, ctx)
        elif key in ("ml",):
            if p.ml == "inference_api":
                if "inference" not in tr:
                    c.excluded = ("not a model-serving option", ["requirements.ml_features"])
                    return
                if c.id == "model_container":
                    if p.tier_i <= 2 or p.prio["cost"] >= 4:
                        c.add("priorities.cost", 1.0, "small tabular model runs as a container beside the app")
                elif t["provider"] == fam and (p.prio["security"] >= 4 or p.tier_i >= 2):
                    c.add("priorities.security", 1.0, "managed endpoint with model registry, IAM and audit trail")
            elif p.ml == "llm_rag":
                if "llm" not in tr:
                    c.excluded = ("not an LLM provider", ["requirements.ml_features"])
                    return
                if c.id == "self_llm" and not p.restricted:
                    c.add("priorities.cost", -1.0, "GPU servers cost more than API usage at this scale")
            elif p.ml == "training":
                if "inference" not in tr:
                    c.excluded = ("not a model-serving option", ["requirements.ml_features"])
                    return
        elif key == "vector":
            if c.id == "pgvector":
                c.add("database", 2.0, "embeddings in the existing PostgreSQL")
        elif key == "ci_cd":
            if c.id == "host_git_deploy":
                if fam in ("vercel", "netlify", "cloudflare", "github") or ctx["static"]:
                    c.add("hosting", 2.5, "Git push deploys with previews are built into the hosting")
                else:
                    c.excluded = ("the hosting platform has no built-in Git deploys", ["hosting"])
                    return
            if c.id == "github_actions":
                c.add("priorities.time_to_market", 0.8, "free minutes, large action marketplace, works with any cloud")
            if c.id == "azure_pipelines" and fam == "azure" and any(
                    k in " ".join(p.existing).lower() for k in ("microsoft 365", "entra", "azure ad")):
                c.add("infrastructure.existing_systems", 0.5, "fits an existing Microsoft estate")
            if c.id == "gitlab_self":
                c.add("infrastructure.deployment_model", 4.0 if p.restricted else -1.0,
                      "CI that runs inside the restricted network" if p.restricted else "self-hosting CI is unnecessary")
        elif key == "mobile_ci":
            want = MOBILE_CI_FOR.get(ctx.get("mobile_id"), "fastlane_gha")
            if c.id == want:
                c.add("frontend", 3.0, f"native build pipeline for {ctx.get('mobile_name')}")
        elif key == "observability":
            if c.id == "host_logs":
                if ctx["static"]:
                    c.add("project.type", 3.0, "static site: platform analytics are enough")
                elif fam in PAAS_FAMILIES:
                    c.add("hosting", 2.0, "the platform's built-in logs, metrics and log drains cover a small team")
                else:
                    c.excluded = ("not enough for a server-side application", ["backend"])
                    return
            elif t["provider"] in HYPERSCALERS and fam not in HYPERSCALERS:
                c.add("hosting", -2.5, "would add a separate cloud account just for monitoring")
            if c.id == "sentry" and (p.mobile or p.web):
                c.add("project.platforms", 0.8, "client-side error tracking for web/mobile")
            if p.region == "india" and t["provider"] == fam:
                c.notes.append("CERT-In requires ICT logs to be retained for 180 days within India")
        elif key == "offline_sync":
            want = "firestore_offline_sync" if bid == "firebase" else OFFLINE_FOR.get(ctx.get("mobile_id"))
            if c.id == want:
                c.add("frontend", 3.0, f"offline store designed for {ctx.get('mobile_name')}")
            if c.id == "powersync" and ctx["engine"] in POSTGRES:
                c.add("database", 0.5, "syncs PostgreSQL to on-device SQLite")
        elif key == "email":
            if c.id == "smtp_self":
                c.add("infrastructure.deployment_model", 2.0 if p.restricted else -2.0, "in-network SMTP relay")
        elif key == "integration":
            if c.id == "hybrid_link":
                c.add("hosting", 3.0 if fam == "azure" else -5.0, "native to App Service")
        elif key == "game_backend":
            pass
    return fn


def prov_in(t, provs):
    return t["provider"] in provs


def _auth_factors(c, p, ctx):
    t, tr = c.t, c.t["traits"]
    bid = ctx["backend_id"]
    a = p.auth
    if a == "enterprise_sso":
        if "saml" not in tr and "enterprise" not in tr:
            c.excluded = ("no SAML/OIDC enterprise federation", ["requirements.auth"])
            return
        if c.id == "framework_auth":
            c.excluded = ("hand-rolling SAML/OIDC federation is a security risk", ["requirements.auth"])
            return
        if c.id == "entra_id":
            ms = any(k in " ".join(p.existing).lower() for k in ("entra", "azure ad", "active directory", "microsoft 365"))
            if ms:
                pass  # existing_fit already gave +4
            elif p.cloud == "azure":
                c.add("infrastructure.cloud_preference", 1.0, "Azure-native workforce identity")
            else:
                c.add("requirements.auth", -1.0, "workforce directory, not a customer SSO broker")
        if c.id == "workos" and p.multi_tenant:
            c.add("requirements.multi_tenant", 1.5, "per-customer SSO/SCIM connections for a multi-tenant B2B product")
        if c.id == "keycloak":
            c.add("requirements.auth", 0.5, "SAML/OIDC broker with LDAP federation")
    elif a == "phone_otp":
        if "phone_otp" not in tr and "phone_otp_with_sms" not in tr:
            c.excluded = ("no phone/SMS OTP login", ["requirements.auth"])
            return
        if c.id in ("supabase_auth", "firebase_auth"):
            c.add("backend", 2.0, "phone OTP built into the chosen BaaS")
        if c.id == "framework_auth":
            if bid in AUTH_VARIANT:
                c.add("requirements.auth", 1.0, "OTP verification inside the backend; no per-MAU identity fees")
            else:
                c.excluded = ("needs a server framework backend", ["backend"])
                return
    else:
        if a == "social" and "social" not in tr:
            c.excluded = ("no social login", ["requirements.auth"])
            return
        if a == "email_password" and "email" not in tr and c.id != "framework_auth":
            c.excluded = ("no email/password login", ["requirements.auth"])
            return
        if c.id == "entra_id":
            c.excluded = ("workforce identity, not consumer logins", ["requirements.auth"])
            return
        if c.id in ("supabase_auth", "firebase_auth"):
            c.add("backend", 2.0, "auth built into the chosen BaaS")
        if c.id == "framework_auth":
            if bid in AUTH_VARIANT:
                c.add("requirements.auth", 0.8 if a == "email_password" else 0.3, "auth inside the backend; no per-MAU fees")
            else:
                c.excluded = ("needs a server framework backend", ["backend"])
                return
        if p.multi_tenant and "orgs" in tr:
            c.add("requirements.multi_tenant", 1.0, "organisations/teams model for multi-tenant B2B")
    # per-MAU cost pressure
    from .cost import auth_cost
    lo, hi = auth_cost(c.id, p)
    if lo > 0:
        budget_fit(c, p, lo, 0.15, c.t["name"])
        c.add("priorities.cost", -min(2.5, 0.25 * (p.prio["cost"] / 3.0) * (lo / 50.0) ** 0.5),
              f"~${lo:,.0f}+/month in per-user identity fees for {p.users:,} users")


def _payment_factors(c, p, ctx):
    tr = c.t["traits"]
    india = p.effective_residency == "india" or p.region == "india" or "upi" in p.description.lower()
    if india:
        if "india" in tr:
            c.add("infrastructure.data_residency", 2.0, "RBI-authorised Indian gateway: UPI, cards and netbanking")
        if "upi" in tr and "upi" in p.description.lower():
            c.add("project.description", 0.8, "native UPI collection as described")
    elif "global" in tr or "mor" in tr:
        c.add("requirements.payments", 0.8, "global card/wallet coverage")
    if any(k in p.description.lower() for k in ("disburs", "payout", "get paid", "providers accept")) or p.type == "marketplace":
        if "payouts" in tr:
            c.add("project.description", 0.8, "payouts/disbursals to providers or borrowers")
    if (p.multi_tenant or p.type == "saas_b2b" or "per seat" in p.description.lower() or "per-seat" in p.description.lower()):
        if "per_seat" in tr:
            c.add("project.description", 1.0, "per-seat subscription billing with proration")
    if "mor" in tr and "gdpr" in p.compliance:
        c.add("compliance", 0.2, "merchant of record handles EU VAT")
    if p.air_gapped:
        c.excluded = ("payment gateways need internet connectivity", ["infrastructure.deployment_model"])


def _evaluate(key, techs, p, ctx, pii=None):
    fn = _layer_fn(key)
    cands = []
    for t in techs:
        c = Cand(t)
        ex = hard_exclusion(t, p, pii=pii)
        if ex:
            c.excluded = ex
        else:
            fn(c, p, ctx)
        cands.append(c)
    return rank(cands)


def _label(key, c, p, ctx):
    bid = ctx["backend_id"]
    eng = ctx["engine"]
    name = c.t["name"]
    if c.id == "ws_native":
        name = WS_VARIANT.get(bid, name)
        if p.tier_i >= 1 or p.ha >= 1:
            name += " + Redis/Valkey pub/sub backplane" if ctx.get("cache") else ""
    elif c.id == "pg_queue":
        v = PGQ_VARIANT.get(bid, "pg-boss")
        if eng == "sqlserver":
            v = "Hangfire (SQL Server storage)"
        name = f"{v} (jobs in the primary database)"
    elif c.id == "redis_jobs":
        name = f"{REDISJ_VARIANT.get(bid, 'BullMQ')} on the Redis/Valkey cache"
    elif c.id == "framework_auth":
        name = AUTH_VARIANT.get(bid, name)
    elif c.id == "host_cdn":
        name = f"Built-in CDN of {ctx['hosting_name']}"
    elif c.id == "host_git_deploy":
        name = f"Git-push deploys on {ctx['hosting_name']}"
    elif c.id == "host_logs":
        name = f"{ctx['hosting_name']} analytics/logs"
    region = _region_label(c, p, ctx["family"])
    if region:
        name = f"{name} ({region})"
    return name, region


def select_supporting(p, fe, be, db_engine, db_off, host):
    static = host.mode == "static"
    bid = be.winner.id if be.winner else None
    baas = bid in ("supabase", "firebase", "appwrite", "pocketbase")
    eng = db_engine.winner.id if db_engine.winner else None
    mob = next((cand for part, cand, *_ in fe.parts if part == "mobile"), None)
    ctx = {"static": static, "backend_id": bid, "engine": eng, "family": host.family,
           "hosting_name": (host.label or "").split(" (")[0], "cache": None,
           "mobile_id": mob.id if mob else None, "mobile_name": mob.t["name"] if mob else None}
    picks = []

    def run(key, layer_name=None, pii=None, required=True):
        techs = layer(layer_name or key)
        ok, ex = _evaluate(key, techs, p, ctx, pii=pii)
        if ok:
            label, region = _label(key, ok[0], p, ctx)
            pk = SupportPick(key, ok[0], ok, ex, label, region)
            picks.append(pk)
            return pk
        if required:
            picks.append(SupportPick(key, None, ok, ex, None))
        return None

    if not static and not baas and (
            (p.realtime and not baas and (p.tier_i >= 1 or p.ha >= 1)) or p.tier_i >= 2
            or (p.p95 and p.p95 <= 200 and p.tier_i >= 1) or (p.workload == "read_heavy" and p.tier_i >= 2)):
        pk = run("cache")
        ctx["cache"] = pk.winner if pk else None
    if not static and p.background_jobs:
        run("queue")
    if p.fts:
        run("search")
    if p.auth != "none":
        pk = run("auth")
        if p.auth == "phone_otp" and not (pk and pk.winner and pk.winner.id == "firebase_auth"):
            run("sms")
    if p.files:
        run("storage")
    if not p.restricted and p.type != "internal_tool" and (
            static or (p.web and (p.seo or p.tier_i >= 2 or p.type in ("content_site", "ecommerce", "marketplace", "social")))
            or (p.files and p.tier_i >= 1 and p.workload != "write_heavy")):
        run("cdn", required=False)
    if p.realtime:
        run("realtime")
        if p.type == "realtime_collab" or ("crdt" in p.signals and p.type not in ("gaming",)):
            run("realtime_crdt")
    if p.payments:
        run("payments")
    if p.ml in ("inference_api", "training"):
        run("ml")
        if p.ml == "training":
            run("ml_training")
    elif p.ml == "llm_rag":
        run("ml")
        run("vector")
    run("ci_cd")
    if p.mobile:
        run("mobile_ci")
    run("observability")
    if p.mobile and ("push" in p.notifications or p.realtime or p.type in ("marketplace", "social")
                     or "notifications" in p.signals or "chat" in p.signals):
        run("push", required=False)
    if not static and ("email" in p.notifications or p.auth == "email_password" or "workflow" in p.signals):
        run("email", required=False)
    if p.offline and p.mobile:
        run("offline_sync")
    if p.geospatial and eng in POSTGRES:
        run("geospatial", required=False)
    if not static and (set(p.compliance) & {"pci_dss", "rbi_localisation", "hipaa", "soc2", "iso27001"}
                       or p.prio["security"] >= 5):
        run("security", required=False)
    if p.deployment == "managed_cloud" and any(
            k in s.lower() for s in p.existing for k in ("on-prem", "on prem", "onprem", "mainframe", "sap ")):
        run("integration", required=False)
    if p.type == "iot":
        run("iot")
    if p.type == "gaming":
        run("game_backend", required=False)
    if p.type == "data_analytics":
        run("analytics", required=False)
    return picks
