"""Knowledge base: technologies, managed offerings, supporting services, lifecycle registry, sources."""
from . import clients, server, supporting  # noqa: F401  (registers entries)
from .common import ALL_TECH, TIERS, REGION_NAMES
from .lifecycle import LIFECYCLE, KB_AS_OF
from .sources import SOURCES

KB_VERSION = "2026.11"

BY_ID = {t["id"]: t for t in ALL_TECH}


def layer(name, include_inactive=False):
    return [t for t in ALL_TECH if t["layer"] == name and (include_inactive or t["status"] == "active")]


def validate_kb():
    """Integrity checks run by tests and at startup of the CLI 'kb' command."""
    problems = []
    seen = set()
    for t in ALL_TECH:
        if t["id"] in seen:
            problems.append(f"duplicate id {t['id']}")
        seen.add(t["id"])
        for s in t["src"]:
            if s not in SOURCES:
                problems.append(f"{t['id']}: unknown source '{s}'")
        if not t["src"]:
            problems.append(f"{t['id']}: no sources")
        for k, v in t["scores"].items():
            if not 1 <= v <= 5:
                problems.append(f"{t['id']}: score {k}={v} out of range")
        if len(t["cost"]) != 5:
            problems.append(f"{t['id']}: cost table must have 5 tiers")
        for lo, hi in t["cost"]:
            if lo > hi:
                problems.append(f"{t['id']}: cost min>max")
    for item in LIFECYCLE:
        if item["src"] not in SOURCES:
            problems.append(f"lifecycle {item['name']}: unknown source {item['src']}")
    return problems


def export():
    """JSON-serialisable view of the knowledge base (for the UI explorer and the report)."""
    techs = []
    for t in sorted(ALL_TECH, key=lambda x: (x["layer"], x["id"])):
        d = dict(t)
        d["traits"] = sorted(t["traits"])
        d["cost"] = [list(p) for p in t["cost"]]
        d["sources"] = [SOURCES[s] for s in t["src"] if s in SOURCES]
        techs.append(d)
    return {"version": KB_VERSION, "as_of": KB_AS_OF, "technologies": techs, "lifecycle": LIFECYCLE,
            "sources": sorted(SOURCES.values(), key=lambda s: s["id"]), "tiers": list(TIERS)}


def stats():
    from collections import Counter
    c = Counter(t["layer"] for t in ALL_TECH if t["status"] == "active")
    inactive = sum(1 for t in ALL_TECH if t["status"] != "active")
    return {"active_by_layer": dict(sorted(c.items())), "inactive_entries": inactive,
            "lifecycle_entries": len(LIFECYCLE), "sources": len(SOURCES), "total": len(ALL_TECH)}
