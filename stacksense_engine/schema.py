"""Input schema for StackSense.

Single source of truth for:
  * validation (types, ranges, enums, required-ness, defaults)
  * the web form (labels, help text, grouping)
  * documentation (why each field matters architecturally, which decisions it drives)

Mandatory fields follow Section 3.1 of the problem statement exactly.
Fields marked ``extra=True`` are StackSense additions; the engine works when they are absent.
"""

PROJECT_TYPES = [
    "content_site", "web_app", "saas_b2b", "ecommerce", "marketplace", "social",
    "realtime_collab", "fintech", "healthtech", "data_analytics", "iot", "ai_ml_product",
    "internal_tool", "gaming", "api_platform", "other",
]
PLATFORMS = ["web", "android", "ios", "desktop", "api_only"]
TRAFFIC = ["steady", "spiky", "seasonal"]
WORKLOAD = ["read_heavy", "balanced", "write_heavy"]
EXPERIENCE = ["beginner", "intermediate", "senior", "mixed"]
CLOUD = ["any", "aws", "gcp", "azure", "none"]
DEPLOYMENT = ["managed_cloud", "self_hosted_cloud_vm", "on_premise", "air_gapped"]
RESIDENCY = ["none", "india", "eu", "us", "other"]
AUTH = ["none", "email_password", "social", "phone_otp", "enterprise_sso"]
ML = ["none", "inference_api", "llm_rag", "training"]
AVAILABILITY = ["99", "99.9", "99.95", "99.99"]
COMPLIANCE = ["gdpr", "dpdp", "hipaa", "pci_dss", "rbi_localisation", "soc2", "iso27001"]
PRIORITY_KEYS = ["cost", "time_to_market", "scalability", "performance", "maintainability", "security"]

# Extra (StackSense) enums
GEOGRAPHY = ["india", "eu", "us", "apac", "latam", "africa", "middle_east", "global"]
LOCK_IN = ["low", "medium", "high"]
NOTIFICATIONS = ["push", "email", "sms", "in_app"]

KNOWN_LANGUAGES = [
    "javascript", "typescript", "python", "java", "kotlin", "csharp", "go", "php", "ruby",
    "rust", "swift", "dart", "elixir", "scala", "cpp", "c", "sql", "html", "css", "r", "fsharp",
    "objective-c", "lua", "gdscript", "bash",
]

# kind: str | int | number | bool | enum | list_enum | list_str | int_or_null | priority
F = []


def field(path, kind, required=False, default=None, enum=None, minimum=None, label="", help="",
          affects=(), extra=False, group=None, nonempty=False, nullable=False):
    F.append({
        "path": path, "kind": kind, "required": required, "default": default, "enum": enum,
        "minimum": minimum, "label": label or path.split(".")[-1].replace("_", " ").capitalize(),
        "help": help, "affects": list(affects), "extra": extra,
        "group": group or path.split(".")[0], "nonempty": nonempty, "nullable": nullable,
    })


# ---------------------------------------------------------------- project
field("project.name", "str", label="Project name", help="Free text, used only for display.")
field("project.type", "enum", True, enum=PROJECT_TYPES, label="Project type",
      help="Sets the domain profile: consistency needs (fintech ledgers), content vs. app, collaboration, game loops.",
      affects=["architecture_style", "frontend", "backend", "database", "supporting"])
field("project.description", "str", label="Description",
      help="Parsed deterministically for signals (GPS, ledger, low-end devices, KYC). Mismatches with structured fields become warnings.",
      affects=["warnings", "supporting"])
field("project.platforms", "list_enum", True, enum=PLATFORMS, nonempty=True, label="Platforms",
      help="Which clients must exist. Web+mobile favours code-sharing (React + React Native); api_only removes the frontend.",
      affects=["frontend", "hosting"])
# ---------------------------------------------------------------- scale
field("scale.users_at_launch", "int", True, minimum=0, label="Users at launch",
      help="Day-one load; drives whether free tiers suffice for the MVP.", affects=["hosting", "cost"])
field("scale.users_12_months", "int", True, minimum=0, label="Users after 12 months",
      help="Design target. Sets the scale tier that sizes compute, database and cost.",
      affects=["architecture_style", "database", "hosting", "cost"])
field("scale.peak_concurrent_users", "int", minimum=0, label="Peak concurrent users",
      help="Concurrency drives connection counts (WebSockets, DB pools) and instance count. Estimated from users if absent.",
      affects=["hosting", "supporting.cache", "supporting.realtime", "cost"])
field("scale.traffic_pattern", "enum", default="steady", enum=TRAFFIC, label="Traffic pattern",
      help="Spiky/seasonal traffic favours autoscaling and scale-to-zero platforms.", affects=["hosting", "cost"])
field("scale.workload", "enum", default="balanced", enum=WORKLOAD, label="Workload",
      help="Read-heavy favours caching/CDN/static rendering; write-heavy favours queues and write-optimised stores.",
      affects=["database", "supporting.cache", "supporting.queue"])
field("scale.data_volume_gb_12_months", "number", minimum=0, label="Data volume after 12 months (GB)",
      help="Storage size decides single-node vs distributed databases and storage cost.", affects=["database", "cost"])
# ---------------------------------------------------------------- team
field("team.size", "int", True, minimum=1, label="Team size",
      help="Small teams cannot operate microservices; architecture style is bounded by team size.",
      affects=["architecture_style", "hosting"])
field("team.experience", "enum", True, enum=EXPERIENCE, label="Experience",
      help="Beginners need gentle learning curves and managed platforms; skill fit weighs more for them.",
      affects=["frontend", "backend", "hosting"])
field("team.languages", "list_str", True, label="Languages",
      help="Strongest single driver of framework choice. Lower-case names, e.g. typescript, python, java, csharp, go.",
      affects=["frontend", "backend"])
field("team.has_devops", "bool", default=False, label="Has DevOps",
      help="Without an operator, high-ops options (Kubernetes, self-managed DBs) are penalised.",
      affects=["hosting", "database", "architecture_style"])
# ---------------------------------------------------------------- budget/timeline
field("budget.monthly_infra_usd", "number", True, minimum=0, label="Monthly infra budget (USD)",
      help="Soft constraint. If the cost floor exceeds it the engine re-plans for cost and flags it.",
      affects=["hosting", "database", "supporting", "cost"])
field("timeline.mvp_weeks", "int", True, minimum=1, label="MVP timeline (weeks)",
      help="Short timelines amplify skill fit and batteries-included frameworks; checked against platform count.",
      affects=["frontend", "backend", "warnings"])
# ---------------------------------------------------------------- infrastructure
field("infrastructure.cloud_preference", "enum", default="any", enum=CLOUD, label="Cloud preference",
      help="Hard constraint when explicit. 'none' means no public cloud.", affects=["hosting", "database", "supporting"])
field("infrastructure.deployment_model", "enum", default="managed_cloud", enum=DEPLOYMENT, label="Deployment model",
      help="Hard constraint. On-premise/air-gapped allow only self-hostable components (no SaaS, no CDN).",
      affects=["hosting", "backend", "database", "supporting"])
field("infrastructure.data_residency", "enum", default="none", enum=RESIDENCY, label="Data residency",
      help="Hard constraint. Every component that stores or processes personal data must offer a region there.",
      affects=["hosting", "database", "supporting"])
field("infrastructure.existing_systems", "list_str", default=[], label="Existing systems",
      help="Systems to reuse or integrate with. Matched against the knowledge base and the end-of-life registry.",
      affects=["backend", "database", "supporting.auth", "warnings"])
# ---------------------------------------------------------------- requirements
field("requirements.realtime", "bool", default=False, label="Realtime",
      help="Needs persistent connections (WebSockets/SSE). Rules out pure request/response serverless backends.",
      affects=["backend", "hosting", "supporting.realtime", "supporting.cache"])
field("requirements.offline_support", "bool", default=False, label="Offline support",
      help="Needs an on-device database and a sync protocol; favours native/cross-platform over PWA.",
      affects=["frontend", "supporting.other"])
field("requirements.full_text_search", "bool", default=False, label="Full-text search",
      help="Postgres FTS up to moderate scale; dedicated engine beyond; static index for static sites.",
      affects=["supporting.search", "database"])
field("requirements.file_media_storage", "bool", default=False, label="File/media storage",
      help="Adds object storage (in-region), upload pipeline and CDN egress cost.",
      affects=["supporting.storage", "supporting.cdn", "cost"])
field("requirements.payments", "bool", default=False, label="Payments",
      help="Adds a payment gateway chosen by geography/compliance (e.g. RBI-regulated aggregators for India).",
      affects=["supporting.payments", "supporting.queue"])
field("requirements.auth", "enum", default="none", enum=AUTH, label="Authentication",
      help="Selects identity provider; phone OTP adds an SMS gateway, enterprise SSO needs SAML/OIDC.",
      affects=["supporting.auth", "backend"])
field("requirements.multi_tenant", "bool", default=False, label="Multi-tenant",
      help="Needs tenant isolation (row-level security, org-aware auth).", affects=["database", "supporting.auth"])
field("requirements.ml_features", "enum", default="none", enum=ML, label="ML features",
      help="Adds model serving, LLM+vector store, or training pipelines; favours Python ecosystems.",
      affects=["backend", "supporting.ml", "cost"])
field("requirements.seo_critical", "bool", default=False, label="SEO critical",
      help="Public pages must be server-rendered or pre-rendered; SPA-only frameworks are penalised.",
      affects=["frontend", "hosting"])
field("requirements.availability", "enum", default="99.9", enum=AVAILABILITY, label="Availability target",
      help="99.95+ requires multi-AZ databases and redundant compute; 99.99 requires multi-region.",
      affects=["hosting", "database", "cost", "warnings"])
field("requirements.p95_latency_ms", "int_or_null", minimum=1, nullable=True, label="p95 latency target (ms)",
      help="Tight targets favour compiled runtimes, in-region hosting, caches.", affects=["backend", "supporting.cache"])
# ---------------------------------------------------------------- compliance / priorities
field("compliance", "list_enum", default=[], enum=COMPLIANCE, label="Compliance",
      help="Hard constraint. Vendors must hold the attestation/BAA; RBI localisation forces India-only storage.",
      affects=["hosting", "database", "supporting"])
for key in PRIORITY_KEYS:
    field(f"priorities.{key}", "priority", default=3, label=key.replace("_", " ").capitalize(),
          help="1-5. Weights the matching quality dimension of every candidate.",
          affects=["all layers"])

# ---------------------------------------------------------------- StackSense extra parameters
field("scale.user_geography", "list_enum", default=None, enum=GEOGRAPHY, extra=True, label="Where users are",
      help="Places compute near users; 'global' or multiple regions adds a CDN and edge rendering preference.",
      affects=["hosting", "supporting.cdn", "warnings"])
field("scale.peak_requests_per_second", "int", minimum=0, extra=True, label="Peak requests/second",
      help="Overrides the concurrency-based estimate for sizing compute and cost.", affects=["hosting", "cost"])
field("team.size_in_12_months", "int", minimum=1, extra=True, label="Team size in 12 months",
      help="Planned hiring; a team growing past ~12 can justify service boundaries later.",
      affects=["architecture_style"])
field("infrastructure.vendor_lock_in_tolerance", "enum", default="medium", enum=LOCK_IN, extra=True,
      label="Vendor lock-in tolerance",
      help="Low tolerance penalises proprietary BaaS/datastores (Firebase, DynamoDB, Cosmos DB).",
      affects=["backend", "database"])
field("infrastructure.existing_licences", "list_str", default=[], extra=True, label="Existing licences/credits",
      help="e.g. microsoft_365, aws_credits, gcp_credits, github_enterprise. Credits bias hosting toward that cloud.",
      affects=["hosting", "supporting.ci_cd"])
field("requirements.notifications", "list_enum", default=[], enum=NOTIFICATIONS, extra=True, label="Notifications",
      help="Push adds FCM/APNs, email adds a transactional email service, sms adds an SMS gateway.",
      affects=["supporting.other", "supporting.queue"])
field("requirements.background_jobs", "bool", default=None, extra=True, label="Background jobs",
      help="Explicitly request a job queue (otherwise inferred from payments, media, ML, notifications).",
      affects=["supporting.queue"])
field("requirements.geospatial", "bool", default=None, extra=True, label="Geospatial queries",
      help="Location search/maps; favours PostgreSQL + PostGIS. Inferred from the description if absent.",
      affects=["database", "supporting.other"])
field("requirements.audit_trail", "bool", default=None, extra=True, label="Immutable audit trail",
      help="Append-only audit log; favours ACID relational stores. Defaults on for fintech/healthtech.",
      affects=["database", "supporting.other"])
field("requirements.rpo_minutes", "int", minimum=0, extra=True, label="Recovery point objective (min)",
      help="Max tolerable data loss. Below 5 minutes requires managed PITR / synchronous replicas.",
      affects=["database", "cost"])

FIELDS = F
FIELD_BY_PATH = {f["path"]: f for f in F}
MANDATORY_PATHS = [f["path"] for f in F if not f["extra"]]
REQUIRED_PATHS = [f["path"] for f in F if f["required"]]
TOP_LEVEL_KEYS = sorted({f["path"].split(".")[0] for f in F} | {"scenario_id"})


def public_schema():
    """Schema description served to the UI."""
    return {"fields": FIELDS, "priority_keys": PRIORITY_KEYS, "known_languages": KNOWN_LANGUAGES}
