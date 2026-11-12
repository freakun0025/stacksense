"""Order-of-magnitude monthly cost model (USD).

Each selected component contributes a (min, max) band from its knowledge-base price table for the
project's scale tier, adjusted by explicit multipliers (availability, team seats) and unit costs
(storage GB, egress GB, identity MAU, SMS OTPs). Every adjustment is listed in ``assumptions``.
"""
import math

from .select_core import ha_multiplier

# identity pricing: (free MAU, USD per MAU above free)
AUTH_MAU = {"cognito": (10_000, 0.0055), "auth0": (25_000, 0.07), "clerk": (10_000, 0.02), "workos": (1_000_000, 0.0025),
            "supabase_auth": (100_000, 0.00325), "firebase_auth": (50_000, 0.0055)}
SMS_PRICE = {"msg91": (0.0025, 0.004), "sns_sms": (0.0025, 0.005), "twilio_verify": (0.05, 0.09),
             "azure_comm_sms": (0.01, 0.03), "self_sms_modem": (0.001, 0.003)}
STORAGE_GB = {"s3": (0.023, 0.026), "gcs": (0.020, 0.023), "azure_blob": (0.018, 0.021), "supabase_storage": (0.021, 0.021),
              "r2": (0.015, 0.015), "do_spaces": (0.02, 0.02), "seaweedfs": (0.005, 0.01), "ceph_rgw": (0.005, 0.01)}
EGRESS_GB = {"s3": (0.0, 0.11), "gcs": (0.08, 0.12), "azure_blob": (0.08, 0.087), "supabase_storage": (0.09, 0.09),
             "r2": (0.0, 0.0), "do_spaces": (0.01, 0.01), "seaweedfs": (0.0, 0.0), "ceph_rgw": (0.0, 0.0)}


def auth_cost(auth_id, p):
    if auth_id in AUTH_MAU:
        free, rate = AUTH_MAU[auth_id]
        over = max(0, p.users - free)
        return round(over * rate * 0.7, 2), round(over * rate, 2)
    return 0.0, 0.0


def _nice_floor(x):
    if x < 20:
        return int(math.floor(x))
    step = 5 if x < 200 else 10 if x < 1000 else 50 if x < 5000 else 100
    return int(math.floor(x / step) * step)


def _nice_ceil(x):
    if x < 20:
        return int(math.ceil(x))
    step = 5 if x < 200 else 10 if x < 1000 else 50 if x < 5000 else 100
    return int(math.ceil(x / step) * step)


def estimate(p, fe, be, db_engine, db_off, host, picks):
    items = []
    notes = []

    def add(name, lo, hi, basis):
        items.append({"component": name, "min": round(lo, 2), "max": round(hi, 2), "basis": basis})

    tier = p.tier_i
    # ---------------- hosting
    h = host.winner
    if h is not None and h.t["layer"] == "hosting":
        lo, hi = h.t["cost"][tier]
        basis = f"{p.tier} tier (~{p.peak_rps:,} req/s peak, {p.peak_cc:,} concurrent users)"
        if host.mode == "app" and "containers" in h.t["traits"] and p.ha >= 2:
            m = 2.2 if p.ha == 3 else 1.5
            lo, hi = lo * m, hi * m
            basis += f"; x{m} for redundant instances (availability {p.availability}%)"
        if h.id == "vercel":
            personal = p.type == "content_site" and p.team_size == 1 and not p.payments
            if not personal:
                lo, hi = lo + 20 * p.team_size, hi + 20 * p.team_size
                basis += f"; Pro plan $20 x {p.team_size} members (Hobby is non-commercial)"
        add(host.label, lo, hi, basis)
    # ---------------- database
    o = db_off.winner
    if o is not None:
        m = ha_multiplier(o.t, p)
        lo, hi = o.t["cost"][tier]
        lo, hi = lo * m, hi * m
        basis = f"{p.tier} tier instance"
        if m != 1.0:
            basis += f"; x{m} for standby/replicas (availability {p.availability}%)"
        included = 8 if o.id == "supabase_pg" else 10 if o.id == "neon_pg" else 20
        extra_gb = max(0.0, p.db_gb - included)
        if extra_gb and o.t["provider"] != "self":
            rate = (0.125, 0.125) if o.id == "supabase_pg" else (0.115, 0.25)
            mm = 2 if (p.ha >= 1 and "ha" in o.t["traits"]) else 1
            lo += extra_gb * rate[0] * mm
            hi += extra_gb * rate[1] * mm
            basis += f"; +{extra_gb:,.0f} GB storage above {included} GB"
        add(o.t["name"], lo, hi, basis)
    # ---------------- supporting
    for pk in picks:
        c = pk.winner
        if c is None:
            continue
        t = c.t
        if pk.key == "auth":
            lo, hi = auth_cost(c.id, p)
            if c.id == "keycloak":
                lo, hi = t["cost"][tier]
            if c.id == "workos" and p.multi_tenant and p.auth == "enterprise_sso":
                lo, hi = lo + 125, hi + 625
                notes.append("WorkOS SSO assumed for 1-5 enterprise customer connections at ~$125 each")
            basis = f"{p.users:,} MAU" + (" (within free tier)" if hi == 0 else "")
            add(pk.label, lo, hi, basis)
        elif pk.key == "sms":
            pr = SMS_PRICE.get(c.id, (0.01, 0.05))
            lo, hi = p.users * 0.3 * pr[0], p.users * 1.0 * pr[1]
            add(pk.label, lo, hi, f"0.3-1 OTP per user per month x {p.users:,} users at ${pr[0]}-{pr[1]} per SMS")
        elif pk.key == "storage":
            sg = STORAGE_GB.get(c.id, (0.02, 0.026))
            eg = EGRESS_GB.get(c.id, (0.05, 0.11))
            media = max(p.media_gb, 1.0)
            cdn_ids = {x.winner.id for x in picks if x.key == "cdn" and x.winner}
            hit = 0.3 if cdn_ids else 1.0          # ~70% of media served from CDN cache
            egress = p.egress_gb * 0.6 * hit
            free_egress = 1000 if "cloudfront" in cdn_ids else 0
            if c.id == "supabase_storage":
                media_billable = max(0.0, media - 100)
                egress_billable = max(0.0, egress - 250)
            elif c.id == "do_spaces":
                media_billable = max(0.0, media - 250)
                egress_billable = max(0.0, egress - 1000)
                add(pk.label + " base", 5, 5, "flat $5 incl. 250 GB + 1 TB egress")
            else:
                media_billable = media
                egress_billable = max(0.0, egress - free_egress)
            lo = media_billable * sg[0] + egress_billable * eg[0]
            hi = media_billable * sg[1] + egress_billable * eg[1]
            add(pk.label, lo, hi, f"{media:,.0f} GB stored, ~{egress:,.0f} GB/month served")
        elif pk.key in ("payments",):
            notes.append(f"{t['name']} charges per transaction (typically ~2% domestic); not counted as infrastructure")
        else:
            lo, hi = t["cost"][tier]
            if pk.key == "cache" and p.ha >= 2:
                lo, hi = lo * 1.5, hi * 1.5
            if lo == 0 and hi == 0:
                continue
            add(pk.label, lo, hi, f"{p.tier} tier")
    total_lo = sum(i["min"] for i in items)
    total_hi = sum(i["max"] for i in items)
    total_hi = max(total_hi, total_lo)
    mn, mx = _nice_floor(total_lo), _nice_ceil(total_hi)
    if mx < mn:
        mx = mn
    assumptions = [
        "Order-of-magnitude band from approximate public list prices (USD) in the knowledge base; not a quote",
        f"Sized for {p.users:,} users at 12 months, {p.peak_cc:,} peak concurrent users, ~{p.peak_rps:,} req/s peak "
        f"(scale tier: {p.tier})",
        f"Data: ~{p.db_gb:,.0f} GB in the database, ~{p.media_gb:,.0f} GB of media, ~{p.egress_gb:,.0f} GB/month egress",
        "Excludes taxes, developer salaries, domain names, app-store fees and one-off migration work",
    ] + notes
    if p.restricted:
        assumptions.append("On-premise figures are amortised hardware/power estimates; staff time not included")
    return {"min": mn, "max": mx, "currency": "USD", "assumptions": assumptions, "breakdown": items}
