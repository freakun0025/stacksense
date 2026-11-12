"""StackSense test-suite (standard library unittest).  Run:  python -m unittest discover -s tests -v"""
import copy
import glob
import json
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from stacksense_engine import kb  # noqa: E402
from stacksense_engine.recommend import recommend, to_json  # noqa: E402
from stacksense_engine.validate import validate  # noqa: E402
from stacksense_engine.describe import parse_description  # noqa: E402
import fuzz  # noqa: E402

STATUSES = {"ok", "ok_with_warnings", "infeasible", "invalid_input"}
STYLES = {"static", "monolith", "modular_monolith", "serverless", "service_oriented", "microservices", "hybrid", "other"}
SUPPORT_LAYERS = {"cache", "queue", "search", "auth", "storage", "cdn", "realtime", "payments", "ml", "ci_cd",
                  "observability", "other"}


def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return json.load(f)


PUBLIC = {f"P{i}": load(f"scenarios/public/P{i}.json") for i in range(1, 7)}


def edge(name):
    return load(glob.glob(os.path.join(ROOT, "scenarios", "edge", name + "*.json"))[0].replace(ROOT + os.sep, ""))


class TestKnowledgeBase(unittest.TestCase):
    def test_integrity(self):
        self.assertEqual(kb.validate_kb(), [])

    def test_coverage_per_core_layer(self):
        st = kb.stats()["active_by_layer"]
        for layer in ("web", "mobile", "backend", "database", "hosting"):
            self.assertGreaterEqual(st[layer], 8, layer)


class TestOutputSchema(unittest.TestCase):
    def check_output(self, r):
        for key in ("status", "summary", "architecture_style", "stack", "estimated_monthly_cost_usd", "warnings",
                    "assumptions", "validation_errors"):
            self.assertIn(key, r)
        self.assertIn(r["status"], STATUSES)
        self.assertIn(r["architecture_style"], STYLES)
        c = r["estimated_monthly_cost_usd"]
        self.assertLessEqual(c["min"], c["max"])
        self.assertIsInstance(c["assumptions"], list)
        for w in r["warnings"]:
            self.assertIn(w["severity"], ("info", "warning", "critical"))
            self.assertTrue(w["code"] and w["message"])
            self.assertIsInstance(w["fields"], list)
        if r["stack"] is None:
            return
        for layer in ("frontend", "backend", "database", "hosting"):
            comp = r["stack"][layer]
            for k in ("choice", "justification", "driven_by", "alternatives"):
                self.assertIn(k, comp, f"{layer}.{k}")
            self.assertTrue(comp["driven_by"], layer)
            self.assertGreaterEqual(len(comp["alternatives"]), 1, layer)
            for a in comp["alternatives"]:
                self.assertTrue(a["choice"] and a["why_not"])
        for s in r["stack"]["supporting"]:
            self.assertIn(s["layer"], SUPPORT_LAYERS)
            self.assertTrue(s["choice"] and s["justification"] and s["driven_by"])

    def test_public_scenarios(self):
        for sid, s in PUBLIC.items():
            with self.subTest(sid):
                r = recommend(s)
                self.check_output(r)
                self.assertIn(r["status"], ("ok", "ok_with_warnings"))

    def test_edge_scenarios_never_crash(self):
        for path in sorted(glob.glob(os.path.join(ROOT, "scenarios", "edge", "*.json"))):
            with self.subTest(os.path.basename(path)):
                with open(path, encoding="utf-8") as f:
                    r = recommend(json.load(f))
                self.check_output(r)
                self.assertFalse(any(e["field"] == "$" for e in r["validation_errors"]))


class TestDeterminism(unittest.TestCase):
    def test_repeat_runs_identical(self):
        for sid, s in PUBLIC.items():
            outs = {to_json(recommend(copy.deepcopy(s))) for _ in range(5)}
            self.assertEqual(len(outs), 1, sid)

    def test_key_order_does_not_matter(self):
        s = PUBLIC["P2"]
        shuffled = json.loads(json.dumps(s, sort_keys=True))
        self.assertEqual(to_json(recommend(s)), to_json(recommend(shuffled)))

    def test_fresh_process_identical(self):
        code = ("import json,sys; sys.path.insert(0, r'%s'); from stacksense_engine.recommend import recommend, to_json;"
                "print(to_json(recommend(json.load(open(r'%s', encoding='utf-8')))))") % (
            ROOT, os.path.join(ROOT, "scenarios", "public", "P4.json"))
        a = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, encoding="utf-8").stdout
        b = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, encoding="utf-8").stdout
        self.assertTrue(a)
        self.assertEqual(a, b)

    def test_llm_switch_does_not_change_stack(self):
        before = os.environ.get("STACKSENSE_LLM")
        try:
            os.environ["STACKSENSE_LLM"] = "on"
            on = [to_json(recommend(s)) for s in PUBLIC.values()]
            os.environ["STACKSENSE_LLM"] = "off"
            off = [to_json(recommend(s)) for s in PUBLIC.values()]
        finally:
            if before is None:
                os.environ.pop("STACKSENSE_LLM", None)
            else:
                os.environ["STACKSENSE_LLM"] = before
        self.assertEqual(on, off)
        self.assertTrue(all(not json.loads(x)["llm_used"] for x in off))


class TestValidation(unittest.TestCase):
    def test_missing_required(self):
        r = recommend(edge("E01"))
        self.assertEqual(r["status"], "invalid_input")
        self.assertIsNone(r["stack"])
        fields = {e["field"] for e in r["validation_errors"]}
        self.assertIn("timeline.mvp_weeks", fields)
        self.assertIn("project.platforms", fields)

    def test_lenient_mode_fills_defaults(self):
        r = recommend(edge("E01"), lenient=True)
        self.assertIn(r["status"], ("ok", "ok_with_warnings"))
        self.assertTrue(any("lenient" in a for a in r["assumptions"]))

    def test_invalid_values_all_reported(self):
        r = recommend(edge("E02"))
        self.assertEqual(r["status"], "invalid_input")
        fields = {e["field"] for e in r["validation_errors"]}
        for f in ("project.type", "scale.users_at_launch", "scale.users_12_months", "team.size", "team.has_devops",
                  "infrastructure.cloud_preference", "requirements.availability", "priorities.cost", "compliance"):
            self.assertIn(f, fields)
        hint = next(e for e in r["validation_errors"] if e["field"] == "infrastructure.cloud_preference")
        self.assertIn('did you mean "aws"', hint["message"])

    def test_non_object_and_garbage(self):
        for raw in (None, [], "text", 42, {"project": "x"}):
            r = recommend(raw)
            self.assertEqual(r["status"], "invalid_input")

    def test_defaults_recorded_as_assumptions(self):
        r = recommend(edge("E20"))
        self.assertIn(r["status"], ("ok", "ok_with_warnings"))
        joined = " ".join(r["assumptions"])
        for f in ("infrastructure.data_residency", "requirements.availability", "priorities.cost",
                  "scale.peak_concurrent_users"):
            self.assertIn(f, joined)

    def test_unknown_fields_are_reported_not_fatal(self):
        s = copy.deepcopy(PUBLIC["P1"])
        s["project"]["favourite_colour"] = "blue"
        r = recommend(s)
        self.assertNotEqual(r["status"], "invalid_input")
        self.assertTrue(any(w["code"] == "UNKNOWN_FIELDS" for w in r["warnings"]))

    def test_validate_function_types(self):
        v = validate({"project": {"type": "web_app", "platforms": ["web"]}, "scale": {"users_at_launch": 1.0,
                      "users_12_months": True}})
        fields = {e["field"] for e in v["errors"]}
        self.assertIn("scale.users_12_months", fields)      # bool is not an integer
        self.assertNotIn("scale.users_at_launch", fields)   # 1.0 is an integral number


class TestPublicScenarioExpectations(unittest.TestCase):
    """Sanity expectations derived from the problem statement (not hard-coded answers)."""

    def test_p1_static_free(self):
        r = recommend(PUBLIC["P1"])
        self.assertEqual(r["architecture_style"], "static")
        self.assertEqual(r["stack"]["backend"]["choice"], "None")
        self.assertEqual(r["stack"]["database"]["choice"], "None")
        self.assertLessEqual(r["estimated_monthly_cost_usd"]["min"], 5)

    def test_india_residency_respected(self):
        for sid in ("P2", "P4", "P5", "P6"):
            r = recommend(PUBLIC[sid])
            for k in ("database", "hosting"):
                choice = r["stack"][k]["choice"]
                self.assertRegex(choice, r"Mumbai|India|Pune|ap-south-1|asia-south1|BLR", f"{sid} {k}: {choice}")

    def test_cloud_preference_respected(self):
        self.assertIn("AWS", recommend(PUBLIC["P4"])["stack"]["hosting"]["choice"])
        self.assertIn("Azure", recommend(PUBLIC["P5"])["stack"]["hosting"]["choice"])

    def test_p4_payments_are_rbi_compliant(self):
        r = recommend(PUBLIC["P4"])
        pay = next(s for s in r["stack"]["supporting"] if s["layer"] == "payments")
        self.assertIn(pay["kb_id"], ("razorpay", "cashfree", "payu"))

    def test_p5_reuses_entra_id(self):
        r = recommend(PUBLIC["P5"])
        auth = next(s for s in r["stack"]["supporting"] if s["layer"] == "auth")
        self.assertEqual(auth["kb_id"], "entra_id")
        self.assertTrue(any(w["code"] == "EXTENDED_SUPPORT_DEPENDENCY" for w in r["warnings"]))

    def test_no_microservices_for_small_teams(self):
        for sid, s in PUBLIC.items():
            self.assertNotEqual(recommend(s)["architecture_style"], "microservices", sid)


class TestEdgeCases(unittest.TestCase):
    def test_contradictory_hard_constraints_infeasible(self):
        for name in ("E09", "E15"):
            r = recommend(edge(name))
            self.assertEqual(r["status"], "infeasible", name)
            self.assertTrue(r["resolution_options"])
            self.assertTrue(any(w["severity"] == "critical" for w in r["warnings"]))

    def test_huge_scale_zero_budget_flagged(self):
        r = recommend(edge("E03"))
        codes = {w["code"] for w in r["warnings"] if w["severity"] == "critical"}
        self.assertIn("BUDGET_EXCEEDED", codes)
        self.assertIn("AVAILABILITY_TEAM_MISMATCH", codes)
        self.assertTrue(any(a.startswith("RELAXED budget") for a in r["assumptions"]))

    def test_air_gapped_only_self_hosted(self):
        r = recommend(edge("E10"))
        ids = [k for _, k in fuzz.chosen_components(r)]
        for kid in ids:
            self.assertTrue(kb.BY_ID[kid]["self_host"], kid)
        self.assertFalse(any(s["layer"] == "cdn" for s in r["stack"]["supporting"]))
        codes = {w["code"] for w in r["warnings"]}
        self.assertIn("PAYMENTS_IMPOSSIBLE_AIRGAPPED", codes)

    def test_static_overengineering_trap(self):
        r = recommend(edge("E06"))
        self.assertEqual(r["architecture_style"], "static")

    def test_eol_existing_systems_warned(self):
        r = recommend(edge("E13"))
        eol = [w for w in r["warnings"] if w["code"] == "END_OF_LIFE_DEPENDENCY"]
        self.assertGreaterEqual(len(eol), 4)
        self.assertTrue(any(w["code"] == "DEPRECATED_SERVICE" for w in r["warnings"]))

    def test_hipaa_vendors(self):
        r = recommend(edge("E08"))
        for _, kid in fuzz.chosen_components(r):
            t = kb.BY_ID[kid]
            if t["provider"] not in (None, "self", "host", "github", "expo", "codemagic") and t["layer"] in (
                    "hosting", "db_offering", "storage"):
                self.assertIn("hipaa", t["compliance"], kid)

    def test_timeline_infeasible_warned(self):
        r = recommend(edge("E05"))
        self.assertTrue(any(w["code"] == "TIMELINE_INFEASIBLE" for w in r["warnings"]))


class TestLocalChanges(unittest.TestCase):
    def test_cosmetic_change_keeps_stack(self):
        s = copy.deepcopy(PUBLIC["P3"])
        s["project"]["name"] = "Renamed"
        a, b = recommend(PUBLIC["P3"]), recommend(s)
        for k in ("frontend", "backend", "database", "hosting"):
            self.assertEqual(a["stack"][k]["choice"], b["stack"][k]["choice"])

    def test_residency_change_moves_region_only(self):
        s = copy.deepcopy(PUBLIC["P6"])
        s["infrastructure"]["data_residency"] = "eu"
        s["compliance"] = ["gdpr"]
        r = recommend(s)
        self.assertNotRegex(r["stack"]["hosting"]["choice"] + r["stack"]["database"]["choice"], r"Mumbai|India")


class TestDescriptionParser(unittest.TestCase):
    def test_p6_signals(self):
        res = parse_description(PUBLIC["P6"]["project"]["description"])
        self.assertIn("geospatial", res["signals"])
        self.assertIn("low_end_devices", res["signals"])
        fields = {(s["field"], str(s["value"])) for s in res["suggestions"]}
        self.assertIn(("requirements.offline_support", "True"), fields)


class TestFuzz(unittest.TestCase):
    def test_random_scenarios_hold_invariants(self):
        stats = fuzz.run_fuzz(300, seed=11)
        self.assertEqual(stats["failures"], [], stats["failures"][:5])


if __name__ == "__main__":
    unittest.main(verbosity=2)
