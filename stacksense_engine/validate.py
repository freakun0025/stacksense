"""Validation and normalisation of scenario input.

Never raises on bad input: every problem becomes a field-level entry in ``errors``.
Defaults for absent optional fields are applied and recorded in ``assumptions``.
"""
import copy
import math

from .schema import FIELDS, FIELD_BY_PATH, KNOWN_LANGUAGES

_MISSING = object()

# Lenient-mode fallbacks for *required* fields (only used with lenient=True).
LENIENT_DEFAULTS = {
    "project.type": "other",
    "project.platforms": ["web"],
    "scale.users_at_launch": 100,
    "scale.users_12_months": None,  # copied from users_at_launch * 10 below
    "team.size": 1,
    "team.experience": "intermediate",
    "team.languages": [],
    "budget.monthly_infra_usd": 50,
    "timeline.mvp_weeks": 12,
}


def _get(d, path):
    cur = d
    for part in path.split("."):
        if not isinstance(cur, dict):
            return _MISSING
        if part not in cur:
            return _MISSING
        cur = cur[part]
    return cur


def _set(d, path, value):
    parts = path.split(".")
    cur = d
    for part in parts[:-1]:
        if not isinstance(cur.get(part), dict):
            cur[part] = {}
        cur = cur[part]
    cur[parts[-1]] = value


def _levenshtein(a, b):
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _suggest(value, options):
    if not isinstance(value, str):
        return None
    low = value.strip().lower().replace("-", "_").replace(" ", "_")
    if low in options:
        return low
    best = sorted(options, key=lambda o: (_levenshtein(low, o), o))[0]
    return best if _levenshtein(low, best) <= max(2, len(best) // 3) else None


def _is_int(v):
    if isinstance(v, bool):
        return False
    if isinstance(v, int):
        return True
    return isinstance(v, float) and math.isfinite(v) and v.is_integer()


def _is_number(v):
    return (isinstance(v, (int, float)) and not isinstance(v, bool)
            and (not isinstance(v, float) or math.isfinite(v)))


def _fmt(v):
    if isinstance(v, str):
        return f'"{v}"'
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


def _tname(v):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "boolean"
    if isinstance(v, int):
        return "integer"
    if isinstance(v, float):
        return "number"
    if isinstance(v, str):
        return "string"
    if isinstance(v, list):
        return "list"
    if isinstance(v, dict):
        return "object"
    return type(v).__name__


def _check_value(spec, value, errors, notes):
    """Return normalised value or _MISSING (error recorded)."""
    path, kind = spec["path"], spec["kind"]

    def err(msg):
        errors.append({"field": path, "message": msg})
        return _MISSING

    if kind == "str":
        if not isinstance(value, str):
            return err(f"must be a string, got {_tname(value)} {_fmt(value)}")
        return value.strip()
    if kind == "bool":
        if not isinstance(value, bool):
            return err(f"must be a boolean (true/false), got {_tname(value)} {_fmt(value)}")
        return value
    if kind in ("int", "int_or_null"):
        if value is None and kind == "int_or_null":
            return None
        if not _is_int(value):
            return err(f"must be an integer, got {_tname(value)} {_fmt(value)}")
        value = int(value)
        if spec["minimum"] is not None and value < spec["minimum"]:
            return err(f"must be >= {spec['minimum']}, got {value}")
        return value
    if kind == "number":
        if not _is_number(value):
            return err(f"must be a number, got {_tname(value)} {_fmt(value)}")
        if spec["minimum"] is not None and value < spec["minimum"]:
            return err(f"must be >= {spec['minimum']}, got {value}")
        return int(value) if float(value).is_integer() else float(value)
    if kind == "priority":
        if not _is_int(value):
            return err(f"must be an integer from 1 to 5, got {_tname(value)} {_fmt(value)}")
        value = int(value)
        if not 1 <= value <= 5:
            return err(f"must be between 1 and 5, got {value}")
        return value
    if kind == "enum":
        if not isinstance(value, str):
            return err(f"must be one of {spec['enum']}, got {_tname(value)} {_fmt(value)}")
        if value not in spec["enum"]:
            hint = _suggest(value, spec["enum"])
            msg = f"unknown value {_fmt(value)}; allowed: {', '.join(spec['enum'])}"
            if hint:
                msg += f" (did you mean \"{hint}\"?)"
            return err(msg)
        return value
    if kind == "list_enum":
        if not isinstance(value, list):
            return err(f"must be a list, got {_tname(value)} {_fmt(value)}")
        out, bad = [], False
        for i, item in enumerate(value):
            if not isinstance(item, str) or item not in spec["enum"]:
                hint = _suggest(item, spec["enum"]) if isinstance(item, str) else None
                msg = f"item {i}: unknown value {_fmt(item)}; allowed: {', '.join(spec['enum'])}"
                if hint:
                    msg += f" (did you mean \"{hint}\"?)"
                errors.append({"field": path, "message": msg})
                bad = True
            elif item not in out:
                out.append(item)
        if bad:
            return _MISSING
        if len(out) != len(value):
            notes.append(f"{path}: duplicate entries removed")
        if spec["nonempty"] and not out:
            return err("must contain at least one value")
        return out
    if kind == "list_str":
        if not isinstance(value, list):
            return err(f"must be a list of strings, got {_tname(value)} {_fmt(value)}")
        out = []
        for i, item in enumerate(value):
            if not isinstance(item, str):
                return err(f"item {i} must be a string, got {_tname(item)} {_fmt(item)}")
            s = item.strip()
            if path == "team.languages":
                norm = s.lower().replace(" ", "")
                norm = {"c#": "csharp", "js": "javascript", "ts": "typescript", "golang": "go",
                        "c++": "cpp", "node": "javascript", "nodejs": "javascript", "f#": "fsharp",
                        "py": "python", "kt": "kotlin"}.get(norm, norm)
                if norm != s:
                    notes.append(f"team.languages: normalised '{s}' to '{norm}'")
                s = norm
            if s and s not in out:
                out.append(s)
        return out
    return err("unsupported field kind")  # pragma: no cover


def validate(raw, lenient=False):
    """Validate a scenario dict.

    Returns dict with keys: data (normalised input or None), errors, assumptions, notes, unknown_fields.
    """
    errors, assumptions, notes, unknown = [], [], [], []
    if not isinstance(raw, dict):
        return {"data": None, "errors": [{"field": "$", "message": f"scenario must be a JSON object, got {_tname(raw)}"}],
                "assumptions": [], "notes": [], "unknown_fields": []}

    data = {}
    if "scenario_id" in raw:
        sid = raw["scenario_id"]
        if isinstance(sid, (str, int)) and not isinstance(sid, bool):
            data["scenario_id"] = str(sid)
        else:
            errors.append({"field": "scenario_id", "message": f"must be a string, got {_tname(sid)}"})

    # sections that exist but are not objects
    for section in ("project", "scale", "team", "budget", "timeline", "infrastructure", "requirements", "priorities"):
        if section in raw and not isinstance(raw[section], dict):
            errors.append({"field": section, "message": f"must be an object, got {_tname(raw[section])}"})

    for spec in FIELDS:
        path = spec["path"]
        value = _get(raw, path)
        if value is None and not spec["nullable"]:
            if spec["required"]:
                errors.append({"field": path, "message": "is required and must not be null"})
                continue
            notes.append(f"{path}: null treated as absent")
            value = _MISSING
        if value is _MISSING:
            if spec["required"]:
                if lenient and path in LENIENT_DEFAULTS:
                    dv = LENIENT_DEFAULTS[path]
                    if path == "scale.users_12_months":
                        launch = _get(data, "scale.users_at_launch")
                        dv = (launch if isinstance(launch, int) else 100) * 10
                    _set(data, path, copy.deepcopy(dv))
                    assumptions.append(f"{path} was missing (required); lenient mode applied default {_fmt(dv) if not isinstance(dv, list) else dv}")
                else:
                    errors.append({"field": path, "message": "is required but missing"})
                continue
            if spec["default"] is not None and not spec["extra"]:
                _set(data, path, copy.deepcopy(spec["default"]))
                dv = spec["default"]
                shown = dv if isinstance(dv, list) else _fmt(dv)
                assumptions.append(f"{path} not provided; default {shown} applied")
            elif spec["default"] is not None and spec["extra"]:
                _set(data, path, copy.deepcopy(spec["default"]))
            elif spec["nullable"]:
                _set(data, path, None)
                if path == "requirements.p95_latency_ms":
                    pass  # recorded in profile with interpretation
            continue
        checked = _check_value(spec, value, errors, notes)
        if checked is not _MISSING:
            _set(data, path, checked)

    # unknown fields (allowed, ignored, reported)
    known_paths = set(FIELD_BY_PATH)
    known_sections = {p.split(".")[0] for p in known_paths}
    for key, val in raw.items():
        if key == "scenario_id":
            continue
        if key not in known_sections:
            unknown.append(key)
            continue
        if isinstance(val, dict):
            for sub in val:
                if f"{key}.{sub}" not in known_paths:
                    unknown.append(f"{key}.{sub}")

    langs = _get(data, "team.languages")
    if isinstance(langs, list):
        for lang in langs:
            if lang not in KNOWN_LANGUAGES:
                notes.append(f"team.languages: '{lang}' is not in the knowledge base language list; it cannot earn skill-fit credit")

    return {"data": None if errors else data, "errors": errors, "assumptions": assumptions,
            "notes": notes, "unknown_fields": unknown, "partial": data}
