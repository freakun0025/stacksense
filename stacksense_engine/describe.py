"""Deterministic free-text parser for ``project.description``.

No LLM involved. A curated phrase lexicon maps evidence in the description to
(a) *suggested* structured field values the user can accept in the UI, and
(b) *signals* the engine uses for small, transparent refinements (e.g. PostGIS
for GPS data, ACID ledger emphasis, low-end device performance).

Suggestions never overwrite structured input. When the description contradicts a
structured field the engine raises an info-level DESCRIPTION_MISMATCH warning.
"""
import re

# (pattern, field, value, label)
SUGGESTION_RULES = [
    (r"\b(chat|messag\w*|live cursor\w*|real[- ]?time|multiplayer|presence|collaborat\w*|live updates?|co-?edit\w*)\b",
     "requirements.realtime", True, "live interaction"),
    (r"\b(offline|intermittent|no (?:signal|connectivity|internet)|poor connectivity|syncs? when|2g|3g|low[- ]bandwidth|rural|villages?)\b",
     "requirements.offline_support", True, "unreliable connectivity"),
    (r"\b(search\w*|find (?:products|providers|listings)|filter\w* and sort\w*)\b",
     "requirements.full_text_search", True, "search"),
    (r"\b(upload\w*|photos?|images?|videos?|documents?|kyc|attachments?|media|files?|scans?|receipts?)\b",
     "requirements.file_media_storage", True, "user files/media"),
    (r"\b(payments?|pay|pays|paying|paid|checkout|subscriptions?|billing|per[- ]seat|upi|emi|invoices?|wallets?|disburs\w*|refunds?|payouts?|loans?)\b",
     "requirements.payments", True, "money movement"),
    (r"\b(otp|phone number|mobile number|sms login|phone login)\b", "requirements.auth", "phone_otp", "phone login"),
    (r"\b(sso|saml|active directory|azure ad|entra|okta|single sign[- ]on|employees? only|used only by employees)\b",
     "requirements.auth", "enterprise_sso", "corporate identity"),
    (r"\b(google login|sign in with (?:google|apple|github)|social login)\b", "requirements.auth", "social", "social login"),
    (r"\b(tenants?|per[- ]seat|workspaces?|organi[sz]ations? (?:sign up|subscribe)|teams pay|b2b)\b",
     "requirements.multi_tenant", True, "multiple customer organisations"),
    (r"\b(scoring model|credit scor\w*|predict\w*|classif\w*|fraud detect\w*|recommendation engine|recommendations|forecast\w*)\b",
     "requirements.ml_features", "inference_api", "model inference"),
    (r"\b(chatbot|llm|gpt|rag|ai assistant|copilot|semantic search|embeddings?|summari[sz]\w*)\b",
     "requirements.ml_features", "llm_rag", "LLM features"),
    (r"\b(blog|seo|landing pages?|marketing site|public pages?|portfolio|catalog(?:ue)?|storefront)\b",
     "requirements.seo_critical", True, "public discoverable pages"),
    (r"\b(android)\b", "project.platforms", "android", "Android client"),
    (r"\b(ios|iphone|ipad)\b", "project.platforms", "ios", "iOS client"),
    (r"\b(web|website|browser|portal|dashboard)\b", "project.platforms", "web", "web client"),
    (r"\b(desktop|windows app|macos app|electron)\b", "project.platforms", "desktop", "desktop client"),
    (r"\b(public api|developer api|api[- ]only|rest api for partners|sdk)\b", "project.platforms", "api_only", "API product"),
    (r"\b(india|indian|upi|aadhaar|rupees?|inr|rbi|nbfc)\b", "infrastructure.data_residency", "india", "Indian users/regulation"),
    (r"\b(india|indian|upi|aadhaar)\b", "compliance", "dpdp", "Indian personal data (DPDP Act 2023)"),
    (r"\b(upi|nbfc|rbi|lending|loans?|payment aggregator)\b", "compliance", "rbi_localisation", "RBI-regulated payments/lending"),
    (r"\b(card payments?|card data|pci)\b", "compliance", "pci_dss", "card data"),
    (r"\b(eu|europe\w*|gdpr)\b", "compliance", "gdpr", "EU personal data"),
    (r"\b(patients?|health records?|ehr|emr|phi|clinic\w*|hipaa|telemedicine)\b", "compliance", "hipaa", "health data"),
    (r"\b(internal|intranet|back[- ]office|employees?|staff)\b", "project.type", "internal_tool", "internal users"),
    (r"\b(marketplace|book\w* (?:electricians|plumbers|services)|providers? accept|two[- ]sided)\b",
     "project.type", "marketplace", "two-sided marketplace"),
    (r"\b(whiteboard|co-?edit\w*|collaborative editor|figma[- ]like)\b", "project.type", "realtime_collab", "collaborative editing"),
    (r"\b(loans?|lending|ledger|payments app|wallet|neobank|upi)\b", "project.type", "fintech", "financial product"),
    (r"\b(sensors?|telemetry|iot|devices? report|mqtt)\b", "project.type", "iot", "device telemetry"),
    (r"\b(game|multiplayer match|leaderboard|matchmaking)\b", "project.type", "gaming", "game"),
    (r"\b(shop|store|cart|e-?commerce|orders?)\b", "project.type", "ecommerce", "online store"),
]

# Signals used by the engine (small, explained refinements)
SIGNAL_RULES = [
    (r"\b(gps|geo[- ]?tag\w*|locations?|maps?|nearby|geofenc\w*|latitude|coordinates)\b", "geospatial",
     "location data: PostgreSQL + PostGIS handles geo queries"),
    (r"\b(ledger|double[- ]entry|accounting|reconcil\w*|balances?)\b", "ledger",
     "money ledger: strict ACID transactions and an append-only journal"),
    (r"\b(low[- ]end|2 ?gb ram|1 ?gb ram|budget phones|cheap (?:android )?phones|entry[- ]level devices)\b", "low_end_devices",
     "low-end devices: favour lean runtimes and small bundles"),
    (r"\b(2g|3g|intermittent|low[- ]bandwidth|poor connectivity)\b", "poor_network",
     "poor networks: compress images on device and use resumable uploads"),
    (r"\b(kyc|identity documents?|aadhaar|pan card)\b", "kyc",
     "KYC documents: encrypted private object storage with short-lived signed URLs"),
    (r"\b(chat\w*|messag\w*)\b", "chat", "chat: persistent connections and message history"),
    (r"\b(live cursors?|presence|multiplayer|same board|co-?edit\w*)\b", "crdt",
     "concurrent editing: CRDT (Yjs) avoids lost updates"),
    (r"\b(markdown|md files?|static pages?)\b", "markdown_content", "Markdown content: pre-render at build time"),
    (r"\b(approvals?|workflow|requests? and approvals?)\b", "workflow", "approval workflows"),
    (r"\b(notif\w*|alerts?|reminders?)\b", "notifications", "notifications"),
    (r"\b(video|streaming|live stream)\b", "video", "video: transcoding and CDN egress dominate cost"),
    (r"\b(two cities|multiple cities|city[- ]wise|pan[- ]india)\b", "multi_city", "multi-city service area"),
]

_COMPILED_S = [(re.compile(p, re.I), f, v, l) for p, f, v, l in SUGGESTION_RULES]
_COMPILED_G = [(re.compile(p, re.I), k, l) for p, k, l in SIGNAL_RULES]


def parse_description(text):
    """Return {'suggestions': [...], 'signals': {name: {'evidence', 'meaning'}}}. Deterministic."""
    text = text or ""
    suggestions = {}
    for rx, field, value, label in _COMPILED_S:
        m = rx.search(text)
        if not m:
            continue
        key = (field, str(value))
        if key in suggestions:
            continue
        suggestions[key] = {"field": field, "value": value, "evidence": m.group(0), "reason": label}
    # resolve auth: prefer most specific (enterprise_sso > phone_otp > social)
    auths = [s for k, s in suggestions.items() if k[0] == "requirements.auth"]
    if len(auths) > 1:
        order = {"enterprise_sso": 0, "phone_otp": 1, "social": 2}
        keep = sorted(auths, key=lambda s: order.get(s["value"], 9))[0]
        suggestions = {k: s for k, s in suggestions.items() if k[0] != "requirements.auth" or s is keep}
    # ml: llm_rag beats inference_api if both
    mls = [s for k, s in suggestions.items() if k[0] == "requirements.ml_features"]
    if len(mls) > 1:
        suggestions = {k: s for k, s in suggestions.items()
                       if k[0] != "requirements.ml_features" or s["value"] == "llm_rag"}
    # project.type: only first (most specific listed first in rules)
    types = [k for k in suggestions if k[0] == "project.type"]
    for k in types[1:]:
        suggestions.pop(k)

    signals = {}
    for rx, key, meaning in _COMPILED_G:
        m = rx.search(text)
        if m and key not in signals:
            signals[key] = {"evidence": m.group(0), "meaning": meaning}
    ordered = sorted(suggestions.values(), key=lambda s: (s["field"], str(s["value"])))
    return {"suggestions": ordered, "signals": signals}


def mismatches(data, parsed):
    """Description evidence that contradicts structured fields -> list of (field, message)."""
    out = []
    req = data.get("requirements", {})
    for s in parsed["suggestions"]:
        f, v = s["field"], s["value"]
        if f.startswith("requirements.") and isinstance(v, bool):
            key = f.split(".", 1)[1]
            if req.get(key) is False:
                out.append((f, f"Description mentions \"{s['evidence']}\" ({s['reason']}) but {f} is false. "
                               f"Confirm the requirement; the recommendation follows the structured field."))
        elif f == "project.platforms":
            plats = data.get("project", {}).get("platforms", [])
            if v not in plats and v != "web" and "api_only" not in plats:
                out.append((f, f"Description mentions \"{s['evidence']}\" but project.platforms does not include '{v}'."))
        elif f == "requirements.auth" and req.get("auth") == "none":
            out.append((f, f"Description mentions \"{s['evidence']}\" ({s['reason']}) but requirements.auth is 'none'."))
    return out
