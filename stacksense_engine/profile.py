"""Derived requirement profile: turns validated input into the signals the selectors use.

Every estimate made here is written to ``assumptions`` so the user can see and correct it.
"""
import math

from .describe import parse_description
from .kb.common import TIERS

CC_RATIO = {"internal_tool": 0.25, "realtime_collab": 0.08, "gaming": 0.10, "social": 0.05, "content_site": 0.02,
            "iot": 0.5}
MB_PER_USER = {"content_site": 0.05, "internal_tool": 8, "ecommerce": 2, "marketplace": 3, "social": 10, "fintech": 2,
               "healthtech": 10, "data_analytics": 50, "iot": 100, "ai_ml_product": 5, "gaming": 1}
REQ_PER_USER_SEC = {"read_heavy": 0.10, "balanced": 0.15, "write_heavy": 0.20}
EXP_FACTOR = {"beginner": 0.6, "intermediate": 1.0, "mixed": 0.9, "senior": 1.4}
HA_LEVEL = {"99": 0, "99.9": 1, "99.95": 2, "99.99": 3}
COMPLEX_TYPES = {"marketplace", "fintech", "healthtech", "saas_b2b", "ecommerce", "social", "ai_ml_product",
                 "api_platform", "realtime_collab", "gaming", "iot", "data_analytics"}
TYPE_POINTS = {"content_site": 1, "internal_tool": 2, "web_app": 3, "fintech": 6, "healthtech": 6, "marketplace": 5,
               "realtime_collab": 5, "gaming": 6, "social": 5, "saas_b2b": 4, "ecommerce": 4, "iot": 5,
               "data_analytics": 4, "ai_ml_product": 5, "api_platform": 4, "other": 4}


def _tier_for(users, cc):
    by_users = 0 if users <= 5000 else 1 if users <= 50_000 else 2 if users <= 500_000 else 3 if users <= 5_000_000 else 4
    by_cc = 0 if cc <= 100 else 1 if cc <= 1000 else 2 if cc <= 10_000 else 3 if cc <= 100_000 else 4
    return max(by_users, by_cc)


class Profile:
    def __init__(self, data, assumptions):
        self.data = data
        g = lambda path, default=None: _get(data, path, default)  # noqa: E731
        self.name = g("project.name", "") or ""
        self.type = g("project.type")
        self.description = g("project.description", "") or ""
        self.platforms = list(g("project.platforms", []))
        self.web = "web" in self.platforms
        self.android = "android" in self.platforms
        self.ios = "ios" in self.platforms
        self.mobile = self.android or self.ios
        self.desktop = "desktop" in self.platforms
        self.api_only = self.platforms == ["api_only"]
        self.has_api_only = "api_only" in self.platforms

        self.users_launch = g("scale.users_at_launch")
        self.users_12 = g("scale.users_12_months")
        self.users = max(self.users_launch, self.users_12)
        self.traffic = g("scale.traffic_pattern", "steady")
        self.workload = g("scale.workload", "balanced")

        cc = g("scale.peak_concurrent_users")
        self.cc_estimated = cc is None
        if cc is None:
            ratio = CC_RATIO.get(self.type, 0.03)
            cc = max(1, int(math.ceil(self.users * ratio)))
            assumptions.append(f"scale.peak_concurrent_users not given; estimated {cc:,} "
                               f"({int(ratio * 100)}% of {self.users:,} users, typical for {self.type})")
        self.peak_cc = cc

        rps = g("scale.peak_requests_per_second")
        if rps is None:
            rps = max(1, int(math.ceil(self.peak_cc * REQ_PER_USER_SEC[self.workload])))
            self.rps_estimated = True
        else:
            self.rps_estimated = False
        self.peak_rps = rps

        dv = g("scale.data_volume_gb_12_months")
        if dv is None:
            mb = MB_PER_USER.get(self.type, 2) * (5 if g("requirements.file_media_storage", False) else 1)
            dv = max(1, round(self.users * mb / 1024))
            assumptions.append(f"scale.data_volume_gb_12_months not given; estimated {dv:,} GB "
                               f"(~{mb} MB per user for {self.type})")
        self.data_gb = float(dv)

        self.team_size = g("team.size")
        self.exp = g("team.experience")
        self.langs = list(g("team.languages", []))
        self.has_devops = g("team.has_devops", False)
        self.team_future = g("team.size_in_12_months") or self.team_size
        self.budget = float(g("budget.monthly_infra_usd"))
        self.weeks = g("timeline.mvp_weeks")

        self.cloud = g("infrastructure.cloud_preference", "any")
        self.deployment = g("infrastructure.deployment_model", "managed_cloud")
        self.residency = g("infrastructure.data_residency", "none")
        self.existing = list(g("infrastructure.existing_systems", []))
        self.lock_tolerance = g("infrastructure.vendor_lock_in_tolerance", "medium")
        self.licences = [s.lower() for s in g("infrastructure.existing_licences", [])]

        self.realtime = g("requirements.realtime", False)
        self.offline = g("requirements.offline_support", False)
        self.fts = g("requirements.full_text_search", False)
        self.files = g("requirements.file_media_storage", False)
        self.payments = g("requirements.payments", False)
        self.auth = g("requirements.auth", "none")
        self.multi_tenant = g("requirements.multi_tenant", False)
        self.ml = g("requirements.ml_features", "none")
        self.seo = g("requirements.seo_critical", False)
        self.availability = g("requirements.availability", "99.9")
        self.ha = HA_LEVEL[self.availability]
        self.p95 = g("requirements.p95_latency_ms")
        self.compliance = sorted(g("compliance", []))
        self.prio = {k: g(f"priorities.{k}", 3) for k in
                     ("cost", "time_to_market", "scalability", "performance", "maintainability", "security")}

        # description signals (deterministic)
        parsed = parse_description(self.description)
        self.parsed_description = parsed
        self.signals = parsed["signals"]
        self.geospatial = g("requirements.geospatial")
        if self.geospatial is None:
            self.geospatial = "geospatial" in self.signals
        self.ledger = "ledger" in self.signals or (self.type == "fintech" and self.payments)
        self.low_end = "low_end_devices" in self.signals
        self.poor_network = "poor_network" in self.signals
        self.audit = g("requirements.audit_trail")
        if self.audit is None:
            self.audit = self.type in ("fintech", "healthtech") or bool({"pci_dss", "hipaa", "rbi_localisation"} & set(self.compliance))
        self.notifications = list(g("requirements.notifications", []) or [])
        bj = g("requirements.background_jobs")
        self.background_jobs = bj if bj is not None else None
        self.rpo = g("requirements.rpo_minutes")
        self.geography = g("scale.user_geography")

        # derived
        self.tier_i = _tier_for(self.users, self.peak_cc)
        self.tier = TIERS[self.tier_i]
        self.media_gb = round(self.data_gb * 0.7, 1) if self.files else 0.0
        self.db_gb = max(1.0, round(self.data_gb - self.media_gb, 1))
        per_user_mb_month = 5 if self.type == "content_site" else 15
        if self.files:
            per_user_mb_month = 30 if "video" not in self.signals else 500
        self.egress_gb = round(self.users * per_user_mb_month / 1024, 1)
        self.restricted = self.deployment in ("on_premise", "air_gapped")
        self.air_gapped = self.deployment == "air_gapped"
        self.vm_only = self.deployment == "self_hosted_cloud_vm"
        self.exp_factor = EXP_FACTOR[self.exp]
        self.forms = bool(_any_word(self.description, ("form", "forms", "register", "registration", "rsvp",
                                                       "contact", "newsletter", "sign up", "signup")))
        dynamic = (self.auth != "none" or self.payments or self.realtime or self.multi_tenant or self.files
                   or self.ml != "none" or self.offline or self.workload == "write_heavy" or self.has_api_only)
        self.needs_backend = dynamic or self.type not in ("content_site", "web_app", "other")
        self.static_eligible = (not dynamic and self.type in ("content_site", "web_app", "other")
                                and set(self.platforms) <= {"web"} and self.workload != "write_heavy")
        self.complex_domain = self.type in COMPLEX_TYPES or (self.payments and self.multi_tenant)
        if self.background_jobs is None:
            self.background_jobs = bool(self.payments or self.files and self.tier_i >= 1 or self.ml != "none"
                                        or self.offline or "push" in self.notifications or "email" in self.notifications
                                        or (self.workload == "write_heavy" and self.traffic == "spiky" and self.tier_i >= 1))
        # effort / capacity (timeline realism)
        pts = TYPE_POINTS.get(self.type, 4)
        pts += 2 * self.realtime + 3 * self.offline + 1 * self.fts + 1 * self.files + 2 * self.payments
        pts += {"none": 0, "email_password": 0.5, "social": 0.5, "phone_otp": 1, "enterprise_sso": 1.5}[self.auth]
        pts += 2 * self.multi_tenant + {"none": 0, "inference_api": 2, "llm_rag": 2, "training": 4}[self.ml]
        client_count = len([p for p in self.platforms if p != "api_only"])
        pts += 2.5 * max(0, client_count - 1)
        pts += sum(2 if c in ("hipaa", "pci_dss", "rbi_localisation") else 1 for c in self.compliance)
        self.feature_points = round(pts, 1)
        self.capacity = round(self.team_size * self.weeks * self.exp_factor, 1)
        self.effort_ratio = round(self.feature_points / max(self.capacity, 0.1), 2)

        # primary region family
        if self.residency != "none":
            self.region = self.residency
        elif self.geography and len(self.geography) == 1 and self.geography[0] in ("india", "eu", "us"):
            self.region = self.geography[0]
            assumptions.append(f"No data_residency; hosting placed in {self.region} where users are (scale.user_geography)")
        elif "gdpr" in self.compliance:
            self.region = "eu"
            assumptions.append("No data_residency given but GDPR applies: primary region placed in the EU to avoid "
                               "international-transfer mechanisms")
        elif "dpdp" in self.compliance or "rbi_localisation" in self.compliance or "india" in self.signals_text():
            self.region = "india"
            assumptions.append("No data_residency given; Indian regulation/users detected, so the primary region is India")
        else:
            self.region = "us"
            if self.needs_backend:
                assumptions.append("No data_residency or user geography given; primary region defaults to US East "
                                   "(move it next to your users)")
        if "rbi_localisation" in self.compliance and self.residency == "none":
            assumptions.append("compliance includes rbi_localisation: payment data must be stored only in India, "
                               "so India residency is enforced as a hard constraint")
        self.effective_residency = "india" if "rbi_localisation" in self.compliance else self.residency
        if self.p95 is None and self.needs_backend:
            assumptions.append("requirements.p95_latency_ms is null: no latency-driven selection applied "
                               "(interactive apps assume ~500 ms is acceptable)")

    def signals_text(self):
        return " ".join(s.get("evidence", "").lower() for s in self.parsed_description["suggestions"]
                        if s["field"] == "infrastructure.data_residency")

    def summary(self):
        return {
            "scale_tier": self.tier, "users_design_target": self.users, "peak_concurrent_users": self.peak_cc,
            "peak_rps_estimate": self.peak_rps, "data_gb": self.data_gb, "db_gb": self.db_gb, "media_gb": self.media_gb,
            "egress_gb_month": self.egress_gb, "primary_region": self.region,
            "effective_residency": self.effective_residency, "needs_backend": self.needs_backend,
            "static_eligible": self.static_eligible, "complex_domain": self.complex_domain,
            "feature_points": self.feature_points, "team_capacity": self.capacity, "effort_ratio": self.effort_ratio,
            "background_jobs": self.background_jobs, "geospatial": self.geospatial, "ledger": self.ledger,
            "low_end_devices": self.low_end, "audit_trail": self.audit,
            "description_signals": sorted(self.signals),
        }


def _any_word(text, words):
    low = (text or "").lower()
    import re
    return any(re.search(r"\b" + re.escape(w) + r"\b", low) for w in words)


def _get(d, path, default=None):
    cur = d
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur
