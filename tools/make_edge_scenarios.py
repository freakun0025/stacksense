"""Generates the edge-case scenario files in scenarios/edge/ (run once; files are committed)."""
import copy
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "scenarios", "edge")


def base(**over):
    s = {
        "project": {"name": "Sample", "type": "web_app", "description": "", "platforms": ["web"]},
        "scale": {"traffic_pattern": "steady", "workload": "balanced", "users_at_launch": 500, "users_12_months": 5000,
                  "peak_concurrent_users": 100, "data_volume_gb_12_months": 10},
        "team": {"has_devops": False, "size": 3, "experience": "intermediate", "languages": ["typescript"]},
        "budget": {"monthly_infra_usd": 200}, "timeline": {"mvp_weeks": 10},
        "infrastructure": {"cloud_preference": "any", "deployment_model": "managed_cloud", "data_residency": "none",
                           "existing_systems": []},
        "requirements": {"realtime": False, "offline_support": False, "full_text_search": False,
                         "file_media_storage": False, "payments": False, "auth": "email_password",
                         "multi_tenant": False, "ml_features": "none", "seo_critical": False, "availability": "99.9",
                         "p95_latency_ms": 500},
        "compliance": [],
        "priorities": {"cost": 3, "time_to_market": 3, "scalability": 3, "performance": 3, "maintainability": 3,
                       "security": 3},
    }
    for path, val in over.items():
        cur = s
        parts = path.split("__")
        for p in parts[:-1]:
            cur = cur[p]
        cur[parts[-1]] = val
    return s


SCENARIOS = {
    "E01_missing_fields": {"scenario_id": "E01", "project": {"type": "web_app"}, "team": {"size": 2}},
    "E02_invalid_values": {
        "scenario_id": "E02",
        "project": {"name": 42, "type": "crypto_exchange", "platforms": ["web", "smartwatch"]},
        "scale": {"users_at_launch": -10, "users_12_months": "lots", "traffic_pattern": "Spiky", "workload": "balanced"},
        "team": {"size": 0, "experience": "expert", "languages": "python", "has_devops": "yes"},
        "budget": {"monthly_infra_usd": -50}, "timeline": {"mvp_weeks": 2.5},
        "infrastructure": {"cloud_preference": "AWS", "deployment_model": "hybrid", "data_residency": "india"},
        "requirements": {"realtime": "true", "availability": 99.9, "auth": "magic_link", "p95_latency_ms": 0},
        "compliance": ["gdpr", "ccpa"],
        "priorities": {"cost": 7, "time_to_market": 0, "security": 3.5},
    },
    "E03_huge_scale_zero_budget": base(
        scenario_id="E03",
        project__name="NextBigSocial", project__type="social",
        project__description="Social network with photo sharing, chat and a feed for millions of users.",
        project__platforms=["web", "android", "ios"],
        scale__users_at_launch=100000, scale__users_12_months=5000000, scale__peak_concurrent_users=250000,
        scale__data_volume_gb_12_months=20000, scale__traffic_pattern="spiky",
        team__size=1, team__experience="beginner", team__languages=["javascript"],
        budget__monthly_infra_usd=0, timeline__mvp_weeks=4,
        requirements__realtime=True, requirements__file_media_storage=True, requirements__auth="social",
        requirements__availability="99.99", requirements__p95_latency_ms=100),
    "E04_enterprise_availability_solo_beginner": base(
        scenario_id="E04", project__name="ClinicBook", project__type="web_app",
        project__description="Appointment booking for one clinic.",
        team__size=1, team__experience="beginner", team__languages=["python"],
        budget__monthly_infra_usd=100, requirements__availability="99.99"),
    "E05_short_timeline_many_platforms": base(
        scenario_id="E05", project__name="EverywhereApp", project__type="web_app",
        project__platforms=["web", "android", "ios", "desktop"], timeline__mvp_weeks=3,
        team__size=2, team__experience="intermediate", team__languages=["typescript"],
        requirements__realtime=True, requirements__payments=True, requirements__offline_support=True),
    "E06_overengineering_static_high_traffic": base(
        scenario_id="E06", project__name="Launch Microsite", project__type="content_site",
        project__description="Marketing site and documentation for a product launch; static pages written in Markdown.",
        scale__users_at_launch=500000, scale__users_12_months=2000000, scale__peak_concurrent_users=40000,
        scale__workload="read_heavy", scale__traffic_pattern="spiky", scale__data_volume_gb_12_months=2,
        team__size=2, team__languages=["javascript", "html", "css"], budget__monthly_infra_usd=50,
        requirements__auth="none", requirements__seo_critical=True, requirements__availability="99.9",
        priorities__cost=4, priorities__scalability=5),
    "E07_tiny_internal_tool": base(
        scenario_id="E07", project__name="Stockroom", project__type="internal_tool",
        project__description="Inventory checklist for a 40-person warehouse team. Used only by staff.",
        scale__users_at_launch=40, scale__users_12_months=50, scale__peak_concurrent_users=15,
        scale__data_volume_gb_12_months=1, team__size=1, team__experience="intermediate",
        team__languages=["python"], budget__monthly_infra_usd=20, timeline__mvp_weeks=3,
        requirements__auth="email_password", requirements__availability="99", priorities__cost=5,
        priorities__time_to_market=5),
    "E08_hipaa_us_healthtech": base(
        scenario_id="E08", project__name="CarePath", project__type="healthtech",
        project__description="Telemedicine visits with patient records, document uploads and video notes.",
        project__platforms=["web", "ios", "android"],
        scale__users_at_launch=5000, scale__users_12_months=80000, scale__peak_concurrent_users=3000,
        scale__data_volume_gb_12_months=800,
        team__size=6, team__experience="senior", team__languages=["typescript", "python"], team__has_devops=True,
        budget__monthly_infra_usd=4000, timeline__mvp_weeks=20,
        infrastructure__data_residency="us",
        requirements__file_media_storage=True, requirements__auth="email_password", requirements__realtime=True,
        requirements__availability="99.95", compliance=["hipaa", "soc2"], priorities__security=5),
    "E09_rbi_vs_eu_residency": base(
        scenario_id="E09", project__name="EuroPay India", project__type="fintech",
        infrastructure__data_residency="eu", requirements__payments=True,
        compliance=["rbi_localisation", "gdpr"]),
    "E10_air_gapped_defence": base(
        scenario_id="E10", project__name="FieldOps", project__type="internal_tool",
        project__description="Maintenance tracking for a defence facility with document storage and search.",
        team__size=6, team__experience="senior", team__languages=["java", "typescript"], team__has_devops=True,
        budget__monthly_infra_usd=3000, scale__users_at_launch=800, scale__users_12_months=1500,
        infrastructure__cloud_preference="none", infrastructure__deployment_model="air_gapped",
        requirements__payments=True, requirements__auth="phone_otp", requirements__full_text_search=True,
        requirements__file_media_storage=True, requirements__availability="99.95", compliance=["iso27001"]),
    "E11_on_prem_with_aws_preference": base(
        scenario_id="E11", project__name="PlantMES", project__type="internal_tool",
        team__size=4, team__languages=["csharp", "sql"], team__has_devops=True,
        infrastructure__cloud_preference="aws", infrastructure__deployment_model="on_premise",
        infrastructure__existing_systems=["Active Directory (on-prem LDAP)", "SQL Server 2016"],
        requirements__auth="enterprise_sso"),
    "E12_skill_mismatch_php_realtime": base(
        scenario_id="E12", project__name="LiveAuction", project__type="ecommerce",
        project__description="Live auctions with bidding updates every second and payments.",
        team__size=3, team__languages=["php", "javascript"], requirements__realtime=True, requirements__payments=True,
        requirements__seo_critical=True, scale__users_12_months=40000, scale__peak_concurrent_users=4000,
        requirements__p95_latency_ms=150, budget__monthly_infra_usd=600),
    "E13_deprecated_existing_systems": base(
        scenario_id="E13", project__name="LegacyRefresh", project__type="saas_b2b",
        team__size=5, team__languages=["javascript", "csharp"],
        infrastructure__existing_systems=["Heroku (current hosting)", "MySQL 5.7", "Xamarin mobile app",
                                          "Visual Studio App Center", "Node.js 16 API", "MongoDB Realm Device Sync"],
        requirements__multi_tenant=True, compliance=["soc2"]),
    "E14_gdpr_b2b_saas_sso": base(
        scenario_id="E14", project__name="Contractly", project__type="saas_b2b",
        project__description="Contract management for mid-size companies; each customer organisation signs in with its own SSO.",
        scale__users_12_months=20000, scale__peak_concurrent_users=800,
        team__size=6, team__experience="senior", team__languages=["typescript", "python"], team__has_devops=True,
        budget__monthly_infra_usd=1200, infrastructure__data_residency="eu",
        requirements__multi_tenant=True, requirements__auth="enterprise_sso", requirements__full_text_search=True,
        requirements__file_media_storage=True, requirements__payments=True, requirements__ml_features="llm_rag",
        compliance=["gdpr", "soc2", "iso27001"]),
    "E15_cloud_none_managed": base(
        scenario_id="E15", infrastructure__cloud_preference="none", infrastructure__deployment_model="managed_cloud"),
    "E16_iot_telemetry": base(
        scenario_id="E16", project__name="ColdChain", project__type="iot",
        project__description="20,000 refrigeration sensors report temperature telemetry every 30 seconds; alerts to operators.",
        project__platforms=["web"], scale__users_at_launch=200, scale__users_12_months=1000,
        scale__peak_concurrent_users=20000, scale__workload="write_heavy", scale__data_volume_gb_12_months=3000,
        team__size=4, team__languages=["python", "typescript"], team__has_devops=True,
        budget__monthly_infra_usd=1500, infrastructure__cloud_preference="aws", requirements__realtime=True),
    "E17_llm_rag_india": base(
        scenario_id="E17", project__name="KisanMitra", project__type="ai_ml_product",
        project__description="Chatbot answering farmers' questions in Hindi using government scheme documents (RAG).",
        project__platforms=["web", "android"], scale__users_12_months=100000, scale__peak_concurrent_users=2000,
        team__size=4, team__languages=["python", "typescript"], budget__monthly_infra_usd=1500,
        infrastructure__data_residency="india", requirements__ml_features="llm_rag", requirements__auth="phone_otp",
        compliance=["dpdp"]),
    "E18_multiplayer_game": base(
        scenario_id="E18", project__name="ArenaRush", project__type="gaming",
        project__description="Fast-paced multiplayer arena game with matchmaking and leaderboards.",
        project__platforms=["android", "ios"], scale__users_12_months=300000, scale__peak_concurrent_users=15000,
        scale__traffic_pattern="spiky", team__size=8, team__experience="senior", team__languages=["csharp", "go"],
        team__has_devops=True, budget__monthly_infra_usd=5000, requirements__realtime=True,
        requirements__payments=True, requirements__auth="social", requirements__p95_latency_ms=60,
        priorities__performance=5),
    "E19_api_platform": base(
        scenario_id="E19", project__name="GeoAPI", project__type="api_platform",
        project__description="Public geocoding API sold per request to developers.", project__platforms=["api_only"],
        scale__users_12_months=3000, scale__peak_concurrent_users=500, team__size=3, team__languages=["go", "python"],
        requirements__payments=True, requirements__auth="email_password", requirements__seo_critical=True,
        budget__monthly_infra_usd=400),
    "E20_minimal_valid": {
        "scenario_id": "E20", "project": {"type": "marketplace", "platforms": ["web"]},
        "scale": {"users_at_launch": 1000, "users_12_months": 10000}, "team": {"size": 2, "experience": "mixed",
                                                                                "languages": []},
        "budget": {"monthly_infra_usd": 100}, "timeline": {"mvp_weeks": 12}},
}

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, s in SCENARIOS.items():
        with open(os.path.join(OUT, f"{name}.json"), "w", encoding="utf-8", newline="\n") as f:
            json.dump(s, f, indent=2)
    # PDF-appendix variant of P4 (has_devops=false in the PDF, true in the JSON file)
    p4 = json.load(open(os.path.join(HERE, "..", "scenarios", "public", "P4.json"), encoding="utf-8"))
    p4v = copy.deepcopy(p4)
    p4v["scenario_id"] = "P4_pdf_variant"
    p4v["team"]["has_devops"] = False
    with open(os.path.join(OUT, "P4_pdf_variant.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(p4v, f, indent=2)
    print(f"wrote {len(SCENARIOS) + 1} files to {os.path.normpath(OUT)}")
