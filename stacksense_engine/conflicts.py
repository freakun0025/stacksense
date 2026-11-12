"""Contradiction, infeasibility and risk detection -> warnings with severity (info | warning | critical)."""
import re

from .describe import mismatches
from .kb import BY_ID
from .kb.lifecycle import LIFECYCLE, KB_AS_OF
from .scoring import lang_match, HYPERSCALERS, CLOUD_LABEL


def W(code, severity, message, fields):
    return {"code": code, "severity": severity, "message": message, "fields": list(fields)}


def preflight(p):
    """Hard-vs-hard constraint conflicts that no stack can satisfy -> (infeasible, warnings, options)."""
    warns, options = [], []
    if "rbi_localisation" in p.compliance and p.residency in ("eu", "us", "other"):
        warns.append(W("RESIDENCY_COMPLIANCE_CONFLICT", "critical",
                       f"rbi_localisation requires payment data to be stored only in India, but data_residency={p.residency} "
                       f"requires it to stay in that jurisdiction. Both cannot hold.",
                       ["compliance", "infrastructure.data_residency"]))
        options += ["Set infrastructure.data_residency to 'india'",
                    "Remove rbi_localisation if the product does not process Indian payment-system data"]
    if p.cloud == "none" and p.deployment in ("managed_cloud", "self_hosted_cloud_vm"):
        warns.append(W("CLOUD_DEPLOYMENT_CONFLICT", "critical",
                       f"cloud_preference=none (no public cloud) contradicts deployment_model={p.deployment}, which runs on a "
                       f"public cloud.", ["infrastructure.cloud_preference", "infrastructure.deployment_model"]))
        options += ["Set deployment_model to 'on_premise' (or 'air_gapped')",
                    "Set cloud_preference to 'any' (or a specific provider)"]
    if p.cloud in HYPERSCALERS and p.air_gapped:
        warns.append(W("CLOUD_AIRGAP_CONFLICT", "critical",
                       f"cloud_preference={p.cloud} cannot be satisfied by an air-gapped deployment: commercial "
                       f"{CLOUD_LABEL[p.cloud]} regions require internet connectivity.",
                       ["infrastructure.cloud_preference", "infrastructure.deployment_model"]))
        options += ["Set cloud_preference to 'none' for a fully air-gapped on-premise build",
                    "Use deployment_model 'on_premise' with a private connection instead of an air gap"]
    return bool(warns), warns, options


def relax_restricted(p):
    """Requirements that cannot exist under a hard deployment constraint are relaxed *before* selection,
    so the stack never contains a component that would break the constraint. Warnings are raised in analyse()."""
    p.relaxed = {}
    if p.air_gapped:
        if p.payments:
            p.relaxed["payments"] = True
            p.payments = False
        if p.auth in ("phone_otp", "social"):
            p.relaxed["auth"] = p.auth
            p.auth = "enterprise_sso"
        if p.seo:
            p.relaxed["seo"] = True
            p.seo = False


def analyse(p, fe, be, db_engine, db_off, host, picks, cost, unknown_fields, validation_notes):
    """Return (warnings, relaxations) after the stack is chosen."""
    w, relax = [], []
    # ------------------------------------------------ budget
    if cost["min"] > p.budget:
        top = sorted(cost["breakdown"], key=lambda i: -i["min"])[:2]
        drivers = ", ".join(f"{i['component']} (~${i['min']:,.0f})" for i in top)
        severe = cost["min"] > 1.5 * p.budget or (p.budget == 0 and cost["min"] >= 20)
        w.append(W("BUDGET_EXCEEDED", "critical" if severe else "warning",
                   f"Estimated minimum ${cost['min']:,}/month exceeds budget.monthly_infra_usd=${p.budget:,.0f}. "
                   f"Biggest drivers: {drivers}. The stack shown is already the cost-optimised plan.",
                   ["budget.monthly_infra_usd"]))
        relax.append(f"RELAXED budget.monthly_infra_usd: requirements as stated need at least ~${cost['min']:,}/month; "
                     f"raise the budget or reduce scope (fewer platforms, lower availability, defer "
                     f"{'ML, ' if p.ml != 'none' else ''}search/realtime features)")
    elif cost["max"] > p.budget:
        w.append(W("BUDGET_HEADROOM", "info",
                   f"Expected ${cost['min']:,}-{cost['max']:,}/month: the upper end exceeds the ${p.budget:,.0f} budget "
                   f"at peak usage. Set billing alerts.", ["budget.monthly_infra_usd"]))
    # ------------------------------------------------ availability vs team
    if p.ha == 3 and (not p.has_devops or p.team_size <= 2 or p.exp == "beginner"):
        w.append(W("AVAILABILITY_TEAM_MISMATCH", "critical",
                   f"availability=99.99 (~4.3 min downtime/month) needs multi-region failover and 24x7 on-call; a "
                   f"{p.team_size}-person {p.exp} team without DevOps cannot operate that.",
                   ["requirements.availability", "team.size", "team.has_devops", "team.experience"]))
        relax.append("RELAXED requirements.availability: designed for ~99.95% on managed multi-zone services "
                     "(provider SLAs) instead of self-operated 99.99% multi-region failover")
    elif p.ha == 2 and not p.has_devops and p.team_size <= 3:
        w.append(W("AVAILABILITY_TEAM_RISK", "warning",
                   f"availability=99.95 with a {p.team_size}-person team and no DevOps relies entirely on managed "
                   f"multi-zone services and provider SLAs; plan alerting and an on-call rota.",
                   ["requirements.availability", "team.has_devops"]))
    o = db_off.winner
    if o is not None and p.ha == 1 and "ha" in o.t["traits"] and p.prio["cost"] >= 4:
        w.append(W("DB_SINGLE_ZONE", "warning",
                   f"To respect priorities.cost={p.prio['cost']} the database runs as a single-zone primary with automated "
                   f"backups; single-zone managed SLAs are ~99.5%, below the {p.availability}% target. Enabling the HA "
                   f"standby roughly doubles the database line item.",
                   ["requirements.availability", "priorities.cost"]))
    if p.ha == 3:
        w.append(W("MULTI_REGION_REQUIRED", "warning",
                   "99.99% needs active-active or warm-standby in a second region; the stack is multi-zone in one region "
                   "(~99.95%) plus cross-region replicas. Budget for the second region.",
                   ["requirements.availability"]))
    # ------------------------------------------------ timeline / team realism
    if p.effort_ratio > 2.0:
        w.append(W("TIMELINE_INFEASIBLE", "critical",
                   f"Scope (~{p.feature_points} feature points: {len(p.platforms)} platform(s), {p.type} domain, "
                   f"requirements) far exceeds capacity ({p.team_size} {p.exp} engineer(s) x {p.weeks} weeks). "
                   f"Ship one platform first.", ["timeline.mvp_weeks", "team.size", "project.platforms"]))
        relax.append("RELAXED timeline.mvp_weeks: phase the MVP - first platform and core flow only; cross-platform "
                     "frameworks were preferred to limit the number of codebases")
    elif p.effort_ratio > 1.0:
        w.append(W("TIMELINE_RISK", "warning",
                   f"Scope (~{p.feature_points} feature points) is tight for {p.team_size} engineer(s) x {p.weeks} weeks; "
                   f"managed services and batteries-included frameworks were weighted up.",
                   ["timeline.mvp_weeks", "team.size"]))
    clients = [x for x in p.platforms if x != "api_only"]
    if len(clients) >= 3 and p.weeks <= 8:
        w.append(W("MANY_PLATFORMS_SHORT_TIMELINE", "warning",
                   f"{len(clients)} client platforms in {p.weeks} weeks: cross-platform code sharing is assumed; "
                   f"consider launching on one platform first.", ["project.platforms", "timeline.mvp_weeks"]))
    if p.team_size == 1 and p.exp == "mixed":
        w.append(W("TEAM_EXPERIENCE_INCONSISTENT", "warning",
                   "team.experience='mixed' implies several engineers but team.size=1; treated as intermediate-level skill fit.",
                   ["team.experience", "team.size"]))
    if p.tier_i >= 3 and p.team_size <= 2 and host.mode != "static":
        w.append(W("HIGH_SCALE_SMALL_TEAM", "warning",
                   f"{p.users:,} users with {p.team_size} engineer(s): only fully managed, autoscaling services are viable.",
                   ["scale.users_12_months", "team.size"]))
    # ------------------------------------------------ scale sanity
    if p.users_12 < p.users_launch:
        w.append(W("USERS_DECLINE", "info",
                   f"users_12_months ({p.users_12:,}) is below users_at_launch ({p.users_launch:,}); sized for the larger.",
                   ["scale.users_12_months", "scale.users_at_launch"]))
    if not p.cc_estimated and p.peak_cc > max(p.users, 1) and p.type != "iot":
        w.append(W("PEAK_EXCEEDS_USERS", "warning",
                   f"peak_concurrent_users ({p.peak_cc:,}) exceeds total users ({p.users:,}); check the numbers "
                   f"(sizing uses the concurrency figure).", ["scale.peak_concurrent_users", "scale.users_12_months"]))
    if p.data_gb >= 10_000 and db_engine.winner and db_engine.winner.id in ("postgresql", "mysql"):
        w.append(W("DATA_VOLUME_LARGE", "warning",
                   f"{p.data_gb:,.0f} GB in one relational primary needs partitioning/sharding (e.g. Citus) and archival.",
                   ["scale.data_volume_gb_12_months"]))
    if p.peak_cc >= 50_000 and p.realtime:
        w.append(W("REALTIME_SCALE", "warning",
                   f"{p.peak_cc:,} concurrent realtime connections: run a dedicated, horizontally scaled connection tier.",
                   ["scale.peak_concurrent_users", "requirements.realtime"]))
    # ------------------------------------------------ latency
    if p.p95 is not None:
        if p.p95 < 20:
            w.append(W("LATENCY_UNREALISTIC", "critical",
                       f"p95_latency_ms={p.p95} is below typical internet round-trip time; only achievable for in-region "
                       f"users with edge caching.", ["requirements.p95_latency_ms"]))
        elif p.p95 < 50:
            w.append(W("LATENCY_AGGRESSIVE", "warning",
                       f"p95_latency_ms={p.p95} needs users in the same region as the servers and cache-first reads.",
                       ["requirements.p95_latency_ms"]))
        elif p.p95 <= 100 and p.geography and (len(p.geography) > 1 or "global" in p.geography):
            w.append(W("LATENCY_GEOGRAPHY", "warning",
                       f"p95 {p.p95} ms for users in {', '.join(p.geography)} needs multi-region or edge deployment.",
                       ["requirements.p95_latency_ms", "scale.user_geography"]))
    # ------------------------------------------------ platform contradictions
    if p.has_api_only and len(p.platforms) > 1:
        w.append(W("API_ONLY_WITH_CLIENTS", "warning",
                   "project.platforms mixes 'api_only' with client platforms; treated as client apps plus a public API.",
                   ["project.platforms"]))
    if p.seo and not p.web:
        w.append(W("SEO_WITHOUT_WEB", "warning",
                   "seo_critical=true but there is no web platform; SEO applies only to public web pages (consider a "
                   "small marketing site).", ["requirements.seo_critical", "project.platforms"]))
    if p.offline and p.api_only:
        w.append(W("OFFLINE_API_ONLY", "warning", "offline_support=true has no meaning for an api_only product.",
                   ["requirements.offline_support", "project.platforms"]))
    if p.offline and p.web and not p.mobile and not p.desktop:
        w.append(W("OFFLINE_WEB_LIMITS", "info",
                   "Offline on the web relies on service workers + IndexedDB; browsers may evict data and iOS limits "
                   "background sync.", ["requirements.offline_support"]))
    if p.offline:
        w.append(W("OFFLINE_CONFLICT_RESOLUTION", "info",
                   "Offline writes need a conflict policy: client-generated UUIDs, server-authoritative merge or "
                   "per-field last-write-wins, and idempotent sync endpoints.", ["requirements.offline_support"]))
    if p.offline and p.realtime:
        w.append(W("OFFLINE_AND_REALTIME", "info", "Offline + realtime editing implies CRDT-style merging on reconnect.",
                   ["requirements.offline_support", "requirements.realtime"]))
    if p.type == "content_site" and (p.payments or p.realtime or p.multi_tenant):
        w.append(W("CONTENT_SITE_DYNAMIC", "info",
                   "project.type=content_site but dynamic features are required; treated as a dynamic web app.",
                   ["project.type"]))
    # ------------------------------------------------ restricted deployment
    rx = getattr(p, "relaxed", {})
    if p.air_gapped:
        if rx.get("payments"):
            w.append(W("PAYMENTS_IMPOSSIBLE_AIRGAPPED", "critical",
                       "Payments need an external gateway; an air-gapped network cannot reach one.",
                       ["requirements.payments", "infrastructure.deployment_model"]))
            relax.append("RELAXED requirements.payments: no payment gateway in the air-gapped stack; handle payments "
                         "in a separate, internet-facing system")
        if rx.get("auth"):
            w.append(W("AUTH_IMPOSSIBLE_AIRGAPPED", "critical",
                       f"auth={rx['auth']} needs external SMS/social providers unavailable in an air-gapped network.",
                       ["requirements.auth", "infrastructure.deployment_model"]))
            relax.append(f"RELAXED requirements.auth: {rx['auth']} replaced by directory-backed SSO (Keycloak + LDAP) "
                         f"inside the air-gapped network")
        if rx.get("seo"):
            w.append(W("SEO_IMPOSSIBLE_AIRGAPPED", "critical",
                       "seo_critical=true requires public internet pages; an air-gapped system is not crawlable.",
                       ["requirements.seo_critical", "infrastructure.deployment_model"]))
            relax.append("RELAXED requirements.seo_critical: public SEO pages must be a separate public website")
    elif p.deployment == "on_premise":
        ext = [x for x, on in (("payment gateway", p.payments), ("SMS OTP gateway", p.auth == "phone_otp"),
                               ("social identity providers", p.auth == "social")) if on]
        if ext:
            w.append(W("ONPREM_EXTERNAL_DEPENDENCIES", "warning",
                       f"On-premise deployment still needs outbound internet for: {', '.join(ext)}. Only these API calls "
                       f"leave the network; no data is hosted by SaaS.", ["infrastructure.deployment_model"]))
        if p.seo:
            w.append(W("ONPREM_PUBLIC_EXPOSURE", "info",
                       "Public SEO pages from on-premise need a DMZ reverse proxy; no third-party CDN is used.",
                       ["requirements.seo_critical", "infrastructure.deployment_model"]))
    if p.cloud in HYPERSCALERS and p.deployment == "on_premise":
        w.append(W("CLOUD_PREFERENCE_ON_PREMISE", "critical",
                   f"cloud_preference={p.cloud} conflicts with deployment_model=on_premise. Deployment model takes "
                   f"precedence; {CLOUD_LABEL[p.cloud]}'s on-prem offering "
                   f"({'AWS Outposts' if p.cloud == 'aws' else 'Azure Local' if p.cloud == 'azure' else 'Google Distributed Cloud'}) "
                   f"is an option if you need its APIs.", ["infrastructure.cloud_preference", "infrastructure.deployment_model"]))
        relax.append(f"RELAXED infrastructure.cloud_preference: '{p.cloud}' not applied because deployment_model=on_premise")
    # ------------------------------------------------ compliance notes
    if "gdpr" in p.compliance and p.effective_residency in ("india", "us", "other"):
        w.append(W("GDPR_TRANSFER", "warning",
                   f"GDPR data stored in {p.effective_residency} is an international transfer: sign Standard Contractual "
                   f"Clauses and run a transfer impact assessment.", ["compliance", "infrastructure.data_residency"]))
    if "hipaa" in p.compliance:
        w.append(W("HIPAA_BAA", "info",
                   "HIPAA: only BAA-covered services are selected for components touching PHI; sign BAAs before go-live "
                   "and keep PHI out of logs/push payloads.", ["compliance"]))
    if "pci_dss" in p.compliance:
        msg = ("PCI DSS: use the gateway's hosted checkout/tokenisation so card data never touches your servers "
               "(SAQ A scope); only PCI-attested providers were selected.") if p.payments else \
              "compliance lists pci_dss but requirements.payments=false; confirm whether card data is handled."
        w.append(W("PCI_SCOPE", "info", msg, ["compliance", "requirements.payments"]))
    if "rbi_localisation" in p.compliance:
        w.append(W("RBI_LOCALISATION", "info",
                   "RBI data localisation: all payment-system data stays in Indian regions; if any processing happens "
                   "abroad, the data must be deleted there and returned to India within one business day/24 hours.",
                   ["compliance"]))
    if "dpdp" in p.compliance:
        extra = ("India residency is enforced because data_residency=india." if p.effective_residency == "india"
                 else "The Act itself permits cross-border transfer except to notified countries.")
        w.append(W("DPDP_OBLIGATIONS", "info",
                   f"DPDP Act 2023: consent notices, purpose limitation, breach intimation to the Data Protection Board "
                   f"and erasure on request. {extra}", ["compliance"]))
    if {"iso27001", "soc2"} & set(p.compliance):
        w.append(W("CERTIFICATION_IS_PROCESS", "info",
                   "ISO 27001/SOC 2 certify your controls, not the stack: providers with attestations were chosen so "
                   "you inherit their controls, but you still need policies, access reviews and audits.", ["compliance"]))
    if p.region == "india" and host.mode != "static":
        w.append(W("CERT_IN_LOGS", "info",
                   "CERT-In Directions (2022): keep ICT system logs for 180 days within Indian jurisdiction.",
                   ["infrastructure.data_residency"]))
    if p.ml == "llm_rag" and p.effective_residency != "none":
        w.append(W("ML_RESIDENCY", "warning",
                   "Use region-pinned model endpoints and avoid cross-region inference profiles so prompts with personal "
                   "data stay in-region.", ["requirements.ml_features", "infrastructure.data_residency"]))
    # ------------------------------------------------ chosen-stack risks
    if be.winner and be.winner.id == "supabase" and p.region == "india":
        w.append(W("REGIONAL_NETWORK_BLOCK_RISK", "warning",
                   "supabase.co was blocked by several Indian ISPs in Feb 2026 (since restored). Serve the API on your own "
                   "custom domain so clients never depend on supabase.co DNS.", ["infrastructure.data_residency"]))
    for name, cand in (("backend", be.winner), ("database", db_off.winner)):
        if cand and cand.t["lock"] == "high":
            w.append(W("VENDOR_LOCK_IN", "info",
                       f"{cand.t['name']} is proprietary; migrating away later means rewriting the data layer.",
                       ["infrastructure.vendor_lock_in_tolerance"]))
    if host.winner and host.winner.id == "vercel" and p.type == "content_site" and p.team_size == 1 and not p.payments:
        w.append(W("FREE_TIER_LIMITS", "info", "Vercel Hobby is for non-commercial use; switch to Pro if the site earns money.",
                   ["budget.monthly_infra_usd"]))
    if cost["max"] == 0 and host.mode == "static":
        w.append(W("FREE_TIER_LIMITS", "info",
                   "Runs entirely on free tiers; traffic spikes beyond fair-use limits may need a paid plan.",
                   ["budget.monthly_infra_usd", "scale.traffic_pattern"]))
    # skills
    for part, cand, *_ in fe.parts:
        _skill_warning(w, p, cand, f"frontend ({part})")
    if be.winner and "baas" not in be.winner.t["traits"] and be.winner.id != "functions":
        _skill_warning(w, p, be.winner, "backend")
    if not p.langs:
        w.append(W("NO_LANGUAGES", "warning",
                   "team.languages is empty: choices favour mainstream, beginner-friendly options; confirm skills.",
                   ["team.languages"]))
    # missing compliant options
    for pk in picks:
        if pk.winner is None and pk.excluded:
            reasons = "; ".join(sorted({e.excluded[0] for e in pk.excluded})[:3])
            w.append(W("NO_COMPLIANT_OPTION", "critical",
                       f"No {pk.purpose or pk.layer} option satisfies the hard constraints ({reasons}).",
                       sorted({f for e in pk.excluded for f in e.excluded[1]})[:3]))
            relax.append(f"RELAXED {pk.layer}: {pk.purpose or pk.layer} omitted because no option meets the hard constraints")
    # ------------------------------------------------ existing systems & lifecycle
    w.extend(_lifecycle(p))
    w.extend(_existing_reuse(p, picks, db_engine, host))
    # description cross-check
    for field, msg in mismatches(p.data, p.parsed_description):
        w.append(W("DESCRIPTION_MISMATCH", "info", msg, [field, "project.description"]))
    if unknown_fields:
        w.append(W("UNKNOWN_FIELDS", "info", f"Ignored fields not in the schema: {', '.join(unknown_fields[:8])}",
                   unknown_fields[:8]))
    for note in validation_notes:
        w.append(W("INPUT_NORMALISED", "info", note, [note.split(":")[0]]))
    return _dedupe(w), relax


def _skill_warning(w, p, cand, where):
    if not p.langs or not cand.t["langs"]:
        return
    m, lang = lang_match(cand.t["langs"], p.langs)
    if m is not None and m < 1.0:
        sev = "warning" if m == 0 else "info"
        msg = (f"{where}: {cand.t['name']} uses {cand.t['langs'][0]}, which the team does not list; it still won on "
               f"other factors. Budget ramp-up time or hire.") if m == 0 else \
              (f"{where}: {cand.t['name']} uses {lang}, close to the team's {', '.join(p.langs)}; expect a short ramp-up.")
        w.append(W("SKILL_MISMATCH", sev, msg, ["team.languages"]))


def _lifecycle(p):
    out = []
    texts = [(s, "infrastructure.existing_systems") for s in p.existing]
    if p.description:
        texts.append((p.description, "project.description"))
    seen = set()
    for text, field in texts:
        low = text.lower()
        for item in LIFECYCLE:
            if item["name"] in seen:
                continue
            if any(re.search(pat, low) for pat in item["patterns"]):
                seen.add(item["name"])
                kind, date = item["kind"], item["date"]
                if kind == "renamed":
                    out.append(W("EXISTING_SYSTEM_RENAMED", "info",
                                 f"'{text}': {item['note']} Treated as {item['replacement']}.", [field]))
                    continue
                if kind == "eol" or (kind == "extended" and date <= KB_AS_OF):
                    regulated = bool({"pci_dss", "hipaa", "rbi_localisation", "iso27001", "soc2"} & set(p.compliance))
                    sev = "critical" if (regulated and field.startswith("infrastructure")) else "warning"
                    out.append(W("END_OF_LIFE_DEPENDENCY", sev,
                                 f"'{text}' matches {item['name']}, end of life since {date}. It is not recommended; migrate "
                                 f"to {item['replacement']}." + (" Unsupported software breaks patch-management controls "
                                                                 "required by the listed compliance regimes." if sev == "critical" else ""),
                                 [field]))
                elif kind == "extended":
                    soon = date <= _plus_months(KB_AS_OF, 12)
                    out.append(W("EXTENDED_SUPPORT_DEPENDENCY", "warning" if soon else "info",
                                 f"'{text}' ({item['name']}) is out of mainstream support; security fixes only until {date}. "
                                 f"{item['note']} Plan an upgrade to {item['replacement']}.".replace("  ", " "), [field]))
                elif kind in ("maintenance", "closed"):
                    out.append(W("DEPRECATED_SERVICE", "warning",
                                 f"'{text}' ({item['name']}): {item['note'] or kind} Not used in the recommendation; "
                                 f"alternative: {item['replacement']}.", [field]))
    return out


def _existing_reuse(p, picks, db_engine, host):
    out = []
    used = {pk.winner.id: pk for pk in picks if pk.winner}
    for s in p.existing:
        low = s.lower()
        how = None
        if re.search(r"entra|azure ad|active directory", low):
            how = ("reused as the identity provider (OIDC/SAML SSO, group-based roles)"
                   if "entra_id" in used else "integrate via OIDC/SAML federation")
        elif re.search(r"microsoft 365|office 365|\bm365\b|exchange online|teams", low):
            how = "reused for notifications/approvals through Microsoft Graph (Outlook/Teams)"
        elif re.search(r"sql ?server|oracle|mysql|postgres|mongo|db2", low):
            target = db_engine.winner.t["name"] if db_engine.winner else "the new database"
            via = "an App Service Hybrid Connection" if "integration" in {pk.key for pk in picks} and host.family == "azure" \
                else "a site-to-site VPN or scheduled sync job"
            how = (f"kept as the system of record for existing data and integrated via {via}; new data lives in {target} "
                   f"(migrate with Azure DMS/AWS DMS when ready)" if re.search(r"on-?prem", low)
                   else f"reused/migrated into {target}")
        elif re.search(r"sap|salesforce|erp|crm|hrms|workday", low):
            how = "integrated through its REST/OData APIs from a background job"
        elif re.search(r"ldap", low):
            how = "federated through the identity provider's LDAP connector"
        if how:
            out.append(W("EXISTING_SYSTEM_REUSED", "info", f"'{s}': {how}.", ["infrastructure.existing_systems"]))
        elif not any(re.search(pat, low) for item in LIFECYCLE for pat in item["patterns"]):
            out.append(W("EXISTING_SYSTEM_UNMAPPED", "info",
                         f"'{s}' is not in the knowledge base; treated as an external integration via its API.",
                         ["infrastructure.existing_systems"]))
    return out


def _plus_months(iso, months):
    y, m, d = (int(x) for x in iso.split("-"))
    m += months
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    return f"{y:04d}-{m:02d}-{d:02d}"


def _dedupe(ws):
    out, seen = [], set()
    for x in ws:
        key = (x["code"], x["message"])
        if key not in seen:
            seen.add(key)
            out.append(x)
    order = {"critical": 0, "warning": 1, "info": 2}
    out.sort(key=lambda x: (order[x["severity"]], x["code"], x["message"]))
    return out
