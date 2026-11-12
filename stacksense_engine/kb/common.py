"""Shared helpers and constants for the knowledge base.

Score scale (1-5) for each technology, assessed for a *typical* project of the kind it targets:
  perf   - runtime performance / latency headroom
  scale  - how far it scales before re-architecture
  ttm    - time-to-market (batteries, docs, DX)
  maint  - long-term maintainability (typing, structure, maturity, hiring pool)
  cost   - cost efficiency at small-to-medium scale (free tiers, idle cost)
  sec    - secure defaults and compliance track record
Other attributes:
  learn  - 5 = easiest to learn, 1 = steep
  ops    - operational burden, 5 = needs dedicated operators
  mature - production maturity / ecosystem size
Prices are (min, max) USD/month per scale tier (tiny, small, medium, large, xlarge),
approximate public list prices (see sources) for the component's typical footprint.
"""

REGIONS_ALL = ("india", "eu", "us", "other")
REGIONS_NO_INDIA = ("eu", "us", "other")
HYPER_COMPLIANCE = ("gdpr", "dpdp", "hipaa", "pci_dss", "rbi_localisation", "soc2", "iso27001")
TIERS = ("tiny", "small", "medium", "large", "xlarge")

ALL_TECH = []


def price(*pairs):
    assert len(pairs) == 5, pairs
    return tuple((float(a), float(b)) for a, b in pairs)


FREE = price((0, 0), (0, 0), (0, 0), (0, 0), (0, 0))


def tech(id, name, layer, *, kind="", langs=(), plats=(), s=(3, 3, 3, 3, 3, 3), learn=3, ops=2, mature=4,
         traits=(), provider=None, self_host=True, saas=False, regions=REGIONS_ALL, compliance=(),
         pii=True, lock="low", users_max=None, users_min=0, cost=None, strengths=(), limits=(), src=(),
         status="active", status_note="", version="", aliases=(), region_names=None, notes=""):
    perf, scale, ttm, maint, cst, sec = s
    t = {
        "id": id, "name": name, "layer": layer, "kind": kind, "langs": tuple(langs), "plats": tuple(plats),
        "scores": {"performance": perf, "scalability": scale, "time_to_market": ttm,
                   "maintainability": maint, "cost": cst, "security": sec},
        "learn": learn, "ops": ops, "mature": mature, "traits": frozenset(traits),
        "provider": provider, "self_host": self_host, "saas": saas, "regions": tuple(regions),
        "compliance": tuple(compliance), "pii": pii, "lock": lock, "users_max": users_max,
        "users_min": users_min, "cost": cost or FREE, "strengths": list(strengths), "limits": list(limits),
        "src": list(src), "status": status, "status_note": status_note, "version": version,
        "aliases": list(aliases), "region_names": region_names or {}, "notes": notes,
    }
    ALL_TECH.append(t)
    return t


# Canonical region names per provider family (used in choice strings)
REGION_NAMES = {
    "aws": {"india": "ap-south-1 Mumbai", "eu": "eu-central-1 Frankfurt", "us": "us-east-1 N. Virginia",
            "other": "nearest in-country AWS region"},
    "gcp": {"india": "asia-south1 Mumbai", "eu": "europe-west3 Frankfurt", "us": "us-central1 Iowa",
            "other": "nearest in-country GCP region"},
    "azure": {"india": "Central India, Pune", "eu": "Germany West Central", "us": "East US",
              "other": "nearest in-country Azure region"},
    "digitalocean": {"india": "BLR1 Bangalore", "eu": "FRA1 Frankfurt", "us": "NYC3", "other": "SGP1"},
    "supabase": {"india": "ap-south-1 Mumbai", "eu": "eu-central-1 Frankfurt", "us": "us-east-1",
                 "other": "ap-southeast-1"},
    "vercel": {"india": "bom1 Mumbai", "eu": "fra1 Frankfurt", "us": "iad1 Washington DC", "other": "sin1"},
    "render": {"eu": "Frankfurt", "us": "Virginia", "other": "Singapore"},
    "railway": {"eu": "EU West (Amsterdam)", "us": "US East", "other": "Southeast Asia"},
    "fly": {"eu": "fra", "us": "iad", "other": "sin"},
    "neon": {"eu": "aws-eu-central-1", "us": "aws-us-east-1", "other": "aws-ap-southeast-1"},
    "mongodb": {"india": "AWS ap-south-1 Mumbai", "eu": "AWS eu-central-1", "us": "AWS us-east-1",
                "other": "nearest in-country region"},
    "firebase": {"india": "asia-south1 Mumbai", "eu": "europe-west3", "us": "nam5", "other": "nearest region"},
    "appwrite": {"eu": "Frankfurt", "us": "New York", "other": "Sydney"},
    "netlify": {"us": "us-east-2"},
    "self": {"india": "your Indian data centre", "eu": "your EU data centre", "us": "your US data centre",
             "other": "your in-country data centre", "none": "your data centre"},
}
