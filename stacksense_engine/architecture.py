"""Architecture-style decision (deterministic rules with an explicit over-engineering guard)."""


def decide(p, fe, be, host):
    b = be.winner
    fields = []
    if host.mode == "static":
        return ("static", "Pre-rendered pages served from a CDN with no server tier: nothing to patch or scale "
                          "for a read-only site.", ["project.type", "scale.workload", "requirements.auth"])
    future = max(p.team_size, p.team_future)
    guard = []
    if future < 25 or not p.has_devops:
        guard.append(f"microservices rejected: {p.team_size} engineer(s)"
                     + ("" if p.has_devops else ", no DevOps") + " cannot absorb the operational overhead")
    if b is not None and ("baas" in b.t["traits"] or "functions" in b.t["traits"]):
        style = "serverless"
        why = (f"{b.t['name'].split(' (')[0]} provides data, auth and APIs as managed services; custom logic runs as "
               f"functions, so there is no server fleet to operate.")
        fields = ["team.size", "team.has_devops", "priorities.time_to_market"]
    elif future >= 25 and p.has_devops and p.users >= 1_000_000 and p.exp in ("senior", "mixed"):
        style = "microservices"
        why = (f"{future} engineers with DevOps at {p.users:,} users: independently deployable services let teams "
               f"ship without coordinating releases.")
        fields = ["team.size", "team.has_devops", "scale.users_12_months"]
        guard = []
    elif future >= 12 and p.has_devops and p.users >= 200_000:
        style = "service_oriented"
        why = (f"{future} engineers and {p.users:,} users justify a few coarse-grained services along domain lines "
               f"(not fine-grained microservices).")
        fields = ["team.size", "team.has_devops", "scale.users_12_months"]
    elif (p.type in ("realtime_collab", "gaming") and p.realtime and p.peak_cc >= 1000) or \
            (p.type == "iot" and p.tier_i >= 2):
        style = "hybrid"
        what = "stateful realtime collaboration servers" if p.type == "realtime_collab" else \
            "dedicated game/session servers" if p.type == "gaming" else "an ingestion pipeline"
        why = (f"A modular API service for accounts, billing and persistence plus {what} that scale independently "
               f"for {p.peak_cc:,} concurrent connections.")
        fields = ["project.type", "requirements.realtime", "scale.peak_concurrent_users"]
    elif p.team_size >= 3 or p.complex_domain:
        style = "modular_monolith"
        why = (f"One deployable with strict internal modules for the {p.type} domain"
               + (" (e.g. ledger, loans, KYC, payments)" if p.type == "fintech" else
                  " (e.g. bookings, providers, chat, payments)" if p.type == "marketplace" else "")
               + f": a {p.team_size}-engineer team gets clear boundaries without distributed-system overhead; "
                 f"modules can be extracted later if scale demands it.")
        if p.ml != "none":
            why += " The ML model is deployed as a separate service so it can be retrained and scaled independently."
        fields = ["team.size", "project.type", "team.has_devops"]
    else:
        style = "monolith"
        why = (f"A single deployable is the fastest and cheapest option for a {p.team_size}-person team "
               f"building a {p.type} with {p.users:,} users.")
        fields = ["team.size", "project.type", "scale.users_12_months"]
    if guard:
        why += " Over-engineering guard: " + "; ".join(guard) + "."
    return style, why, fields
