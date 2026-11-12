"""OPTIONAL LLM assistance - permitted use #1 of Section 5.1 only (free text -> *suggested* fields).

* OFF by default. Enable with STACKSENSE_LLM=on plus Anthropic credentials (ANTHROPIC_API_KEY) and
  `pip install anthropic`. `python stacksense.py --no-llm ...` or STACKSENSE_LLM=off forces it off.
* Only the web UI's "Suggest with AI" button calls it. The output is shown as suggestions the user must
  accept; it is never passed to the recommendation engine. recommend() does not import this module, so
  the chosen stack is identical with the LLM on or off.
"""
import json
import os

MODEL = os.environ.get("STACKSENSE_LLM_MODEL", "claude-opus-5-5")
ALLOWED_FIELDS = [
    "project.type", "project.platforms", "requirements.realtime", "requirements.offline_support",
    "requirements.full_text_search", "requirements.file_media_storage", "requirements.payments",
    "requirements.auth", "requirements.multi_tenant", "requirements.ml_features", "requirements.seo_critical",
    "infrastructure.data_residency", "compliance", "scale.workload", "scale.traffic_pattern",
]
SCHEMA = {
    "type": "object",
    "properties": {
        "suggestions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "field": {"type": "string", "enum": ALLOWED_FIELDS},
                    "value": {"type": "string"},
                    "evidence": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["field", "value", "evidence", "reason"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["suggestions"],
    "additionalProperties": False,
}
PROMPT = """You help fill in a structured project questionnaire from a free-text description.
Return only fields that the description gives clear evidence for. Quote the exact words as evidence.
Allowed enum values:
project.type: content_site, web_app, saas_b2b, ecommerce, marketplace, social, realtime_collab, fintech, healthtech,
  data_analytics, iot, ai_ml_product, internal_tool, gaming, api_platform, other
project.platforms (one value per suggestion): web, android, ios, desktop, api_only
requirements.auth: none, email_password, social, phone_otp, enterprise_sso
requirements.ml_features: none, inference_api, llm_rag, training
infrastructure.data_residency: none, india, eu, us, other
compliance (one value per suggestion): gdpr, dpdp, hipaa, pci_dss, rbi_localisation, soc2, iso27001
scale.workload: read_heavy, balanced, write_heavy ; scale.traffic_pattern: steady, spiky, seasonal
Boolean requirement fields take "true" or "false".

Description:
"""


def enabled():
    if os.environ.get("STACKSENSE_LLM", "off").lower() not in ("on", "1", "true", "yes"):
        return False
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return True


def status():
    flag = os.environ.get("STACKSENSE_LLM", "off").lower() in ("on", "1", "true", "yes")
    if not flag:
        return {"enabled": False, "message": "OFF (default). The engine is fully deterministic; set STACKSENSE_LLM=on to "
                                             "enable optional AI suggestions for the description field."}
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return {"enabled": False, "message": "STACKSENSE_LLM=on but the 'anthropic' package is not installed "
                                             "(pip install anthropic); deterministic parser only."}
    return {"enabled": True, "message": f"ON for description suggestions only ({MODEL}); never used to choose the stack."}


def _coerce(field, value):
    v = value.strip()
    if field.startswith("requirements.") and v.lower() in ("true", "false") and field not in (
            "requirements.auth", "requirements.ml_features"):
        return v.lower() == "true"
    return v


def suggest_fields(text):
    """Return {'suggestions': [...]} or {'error': ...}. Suggestions only; the caller shows them to the user."""
    if not enabled():
        return {"error": status()["message"], "suggestions": []}
    import anthropic
    client = anthropic.Anthropic()
    try:
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=4000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
            messages=[{"role": "user", "content": PROMPT + (text or "")[:4000]}],
        )
    except anthropic.RateLimitError:
        return {"error": "LLM rate-limited; using the deterministic parser only.", "suggestions": []}
    except anthropic.APIStatusError as e:
        return {"error": f"LLM unavailable (HTTP {e.status_code}); using the deterministic parser only.", "suggestions": []}
    except anthropic.APIConnectionError:
        return {"error": "LLM unreachable (network); using the deterministic parser only.", "suggestions": []}
    if response.stop_reason == "refusal":
        return {"error": "The model declined this description; deterministic suggestions are still shown.",
                "suggestions": []}
    body = next((b.text for b in response.content if b.type == "text"), "")
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return {"error": "LLM returned an unexpected format.", "suggestions": []}
    out = []
    for s in data.get("suggestions", []):
        if s.get("field") in ALLOWED_FIELDS:
            out.append({"field": s["field"], "value": _coerce(s["field"], str(s.get("value", ""))),
                        "evidence": s.get("evidence", ""), "reason": s.get("reason", ""), "source": "llm"})
    return {"suggestions": out, "model": MODEL}
