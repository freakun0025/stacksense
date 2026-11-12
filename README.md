# StackSense - Intelligent Tech Stack Recommendation Engine

**Synergy '26 · StackSense Challenge** · GitHub: <https://github.com/freakun0025/stacksense>

StackSense turns structured project parameters (project type, scale, team skills, budget, timeline,
infrastructure, compliance and priorities) into a recommended **frontend, backend, database and hosting**
plus the supporting services the inputs call for (cache, queue, search, auth, storage, CDN, realtime,
payments, ML, CI/CD, observability). Every decision is made by **deterministic rules and weighted scoring
over a curated, cited knowledge base** (238 technologies and managed offerings, 64 end-of-life records,
285 sources), never by an LLM. Hard constraints - data residency, compliance, deployment model, cloud
preference - exclude non-compliant options outright; budget, timeline and priorities are traded off
explicitly. Each component comes with a justification, the input fields that drove it (`driven_by`),
alternatives with the reason they lost, trade-offs, an order-of-magnitude monthly cost band, and warnings
with severity. Identical input always produces byte-identical JSON. It runs on the Python standard library
alone: no `pip install`, no API keys.

---

## 1. Quick start (under 2 minutes)

```bash
# Windows (PowerShell)                      # macOS / Linux
python --version   # 3.9 or newer           python3 --version
python stacksense.py serve                  python3 stacksense.py serve
```

The web UI opens at **http://localhost:8000**. Pick a sample from **Load a sample** (P1-P6 or an edge case),
press **Recommend stack**, then **Download JSON**.

Run a scenario file from the command line:

```bash
python stacksense.py run scenarios/public/P2.json
# -> prints a summary and writes outputs/P2_output.json
```

---

## 2. System architecture

```
                    scenario JSON  (file / web form / HTTP POST)
                                   |
                     +-------------v--------------+
                     | 1 validate.py              |  types, ranges, enums, required fields, "did you mean"
                     |   schema.py                |  defaults applied -> assumptions[]; errors -> invalid_input
                     +-------------+--------------+
                                   |
                     +-------------v--------------+
                     | 2 profile.py + describe.py |  scale tier, concurrency, req/s, data split, effort vs
                     |                            |  capacity, primary region, description signals (GPS, ledger…)
                     +-------------+--------------+
                                   |
                     +-------------v--------------+
                     | 3 conflicts.preflight      |  hard-vs-hard contradictions -> status "infeasible"
                     |   conflicts.relax_restricted|  impossible requirements (e.g. payments when air-gapped)
                     +-------------+--------------+  relaxed with critical warnings
                                   |
   knowledge base  +---------------v-----------------------------------------------+
   kb/*.py  ------>| 4 select_core.py   frontend -> backend -> database -> hosting  |
   (techs, scores, |   select_support.py supporting services                      |
   regions, certs, |   scoring.py: hard_exclusion() + weighted Factors            |
   prices, EOL,    +---------------+-----------------------------------------------+
   sources)                        |
                     +-------------v--------------+
                     | 5 cost.py                  |  tiered prices x HA multipliers + per-GB/MAU/SMS units
                     |   budget re-plan           |  floor > budget -> re-run with cost weighted at 5
                     +-------------+--------------+
                                   |
                     +-------------v--------------+
                     | 6 architecture.py          |  style + over-engineering guard
                     |   conflicts.analyse        |  warnings (info / warning / critical)
                     |   explain.py               |  justification, driven_by, why-not, trade-offs, trace
                     +-------------+--------------+
                                   |
                     output JSON (Section 4 schema + extras)  -> CLI file / web UI / HTTP response
```

| Module | Responsibility |
|---|---|
| `stacksense.py` | CLI: `run`, `batch`, `validate`, `describe`, `kb`, `serve`; loads optional `.env` |
| `stacksense_engine/schema.py` | Single source of truth for all input fields: type, enum, default, help text, which decisions each field affects |
| `stacksense_engine/validate.py` | Field-level validation; never raises; records defaults as assumptions; optional lenient mode |
| `stacksense_engine/describe.py` | Deterministic phrase lexicon for `project.description`: suggestions + engine signals + mismatch warnings |
| `stacksense_engine/profile.py` | Derived metrics (scale tier, peak req/s, DB vs media GB, effort ratio, region) - every estimate logged |
| `stacksense_engine/kb/` | Knowledge base: `clients.py` (web/mobile/desktop), `server.py` (backends, DB engines, 33 managed DB offerings, hosting), `supporting.py`, `lifecycle.py` (EOL registry), `sources.py` (citations) |
| `stacksense_engine/scoring.py` | `hard_exclusion()` (residency, compliance scopes, deployment model, cloud preference, lifecycle) and reusable soft factors |
| `stacksense_engine/select_core.py` | Layer logic for frontend (web + mobile + desktop), backend, database engine, hosting and managed DB offering |
| `stacksense_engine/select_support.py` | Decides which supporting capabilities are needed and scores providers for each |
| `stacksense_engine/cost.py` | Monthly cost band with explicit assumptions and a per-component breakdown |
| `stacksense_engine/conflicts.py` | Pre-flight infeasibility, relaxations, 50+ warning rules, lifecycle scan of existing systems |
| `stacksense_engine/architecture.py` | Architecture style with an explicit over-engineering guard |
| `stacksense_engine/explain.py` | Converts recorded factors into justifications, `driven_by`, why-not texts, trade-offs and the decision trace |
| `stacksense_engine/recommend.py` | Orchestrator; status; budget re-plan; output assembly |
| `stacksense_engine/server.py` | Zero-dependency HTTP server (JSON API + static UI) |
| `stacksense_engine/llm.py` | **Optional**, off by default: AI suggestions for the description field only |
| `web/` | Vanilla-JS single-page UI (no build step) |

**How a decision is made.** For each layer the engine (1) removes candidates that break a hard constraint
and remembers why, (2) scores the rest as a sum of explicit factors - priorities × knowledge-base scores,
team-language fit weighted by experience and timeline, learning curve, operations burden vs `has_devops`,
scale fit (with over-engineering penalties), budget fit, lock-in tolerance, reuse of existing systems and
layer-specific requirement fit - and (3) ranks deterministically (score, then maturity, then id). The same
factors generate the justification, `driven_by`, the "why not" of each alternative and the `decision_trace`.

---

## 3. Technology used

| Component | Technology | Version |
|---|---|---|
| Engine, CLI, HTTP server | Python standard library only (`json`, `http.server`, `argparse`, `re`, `hashlib`, `unittest`) | Python 3.9+ (developed on 3.11.5) |
| Web UI | HTML5, CSS, vanilla JavaScript (ES2020), no framework, no build | any current browser |
| Container (optional) | Docker image `python:3.12-slim`, Docker Compose v2 | — |
| Optional AI assistant | `anthropic` Python SDK, model `claude-opus-5-5` | `anthropic>=1.0` (not installed by default) |

## 4. Prerequisites

* **Python 3.9 or newer** on Windows, macOS or Linux. Nothing else is required.
  * Windows: use `python` (or `py`); macOS/Linux: use `python3`.
* A modern browser for the UI (Chrome, Edge, Firefox, Safari).
* Optional: Docker Desktop / Docker Engine with Compose v2.
* Port 8000 free (change with `--port 8080` or `STACKSENSE_PORT`).

## 5. Local setup and run (step by step)

```bash
# 1. Get the code
git clone https://github.com/freakun0025/stacksense.git
cd stacksense            # (or unzip source.zip and cd into it)

# 2. (optional) check everything works - 32 tests, ~5 s
python -m unittest discover -s tests

# 3. Start the web UI
python stacksense.py serve                 # http://localhost:8000
python stacksense.py serve --port 8080     # if 8000 is taken
```

**Docker (alternative)**

```bash
docker compose up --build                  # http://localhost:8000
docker compose run --rm stacksense python stacksense.py run scenarios/public/P1.json
```

## 6. Running a scenario JSON and where the output goes

```bash
# one file  -> outputs/<scenario_id>_output.json  (or choose the path with -o)
python stacksense.py run path/to/scenario.json
python stacksense.py run path/to/scenario.json -o results/my_output.json

# many scenarios: a JSON array file (like stacksense_public_scenarios.json) or a directory of files
python stacksense.py batch scenarios/public/stacksense_public_scenarios.json -d outputs
python stacksense.py batch path/to/hidden_scenarios/ -d outputs/hidden

# validate only (field-level errors, defaults that would be applied)
python stacksense.py validate path/to/scenario.json
```

* The CLI prints a human summary (stack, cost, warnings) and writes the full JSON (UTF-8, LF).
* Exit code is `2` for `invalid_input`, otherwise `0`.
* `--lenient` fills missing **required** fields with documented defaults instead of returning `invalid_input`
  (defaults are listed in `assumptions`). Default behaviour is strict, as Section 4 specifies.
* `--no-trace` omits the (extra) `decision_trace` field.
* In the web UI: **Import JSON…** loads any scenario file; **Download JSON** saves the result.

**Output fields** - everything required by Section 4 (`status`, `summary`, `architecture_style`,
`stack.frontend/backend/database/hosting/supporting[]` with `choice`, `justification`, `driven_by`,
`alternatives[{choice, why_not}]`, `tradeoffs`, `estimated_monthly_cost_usd {min, max, assumptions}`,
`warnings[{code, severity, message, fields}]`, `assumptions`, `validation_errors`) plus extras:
`scenario_id`, `engine_version`, `kb_version`, `input_hash`, `architecture_rationale`, per-component
`fit_score`, `confidence`, `kb_id`, `sources`, a cost `breakdown`, the derived `profile`,
`resolution_options` (for `infeasible`) and the `decision_trace`.

## 7. Switching off LLM features

**LLM features are OFF by default and never choose the stack.** The only LLM use is an optional
"Suggest with AI" button that proposes form values from the free-text description (permitted use #1 in
Section 5.1); suggestions must be accepted by the user. `recommend()` never imports the LLM module.

| How | Effect |
|---|---|
| Do nothing | Off (default `STACKSENSE_LLM=off`) |
| `STACKSENSE_LLM=off` (env var or `.env`) | Off |
| `python stacksense.py --no-llm serve` / `--no-llm run ...` | Forces off for that process |
| UI chip **"LLM: off"** in the top bar | Shows the current state |

To enable the optional assistant: `pip install anthropic`, copy `.env.example` to `.env`, set
`STACKSENSE_LLM=on` and `ANTHROPIC_API_KEY=...`. The test `test_llm_switch_does_not_change_stack`
proves the output is identical with the switch on or off.

## 8. Project structure

```
source/
├── README.md                   this file
├── .env.example                optional configuration (no secrets committed)
├── requirements.txt            no required dependencies (optional: anthropic)
├── Dockerfile, docker-compose.yml, .dockerignore
├── stacksense.py               CLI entry point
├── stacksense_engine/          the engine (see module table above)
│   └── kb/                     knowledge base + lifecycle registry + sources
├── web/                        index.html, app.js, styles.css, favicon.svg
├── scenarios/
│   ├── public/                 P1-P6 (+ the original stacksense_public_scenarios.json)
│   └── edge/                   E01-E20 edge cases + P4_pdf_variant (has_devops=false as in the PDF)
├── outputs/                    P1-P6_output.json and outputs/edge/*.json (engine output)
├── tests/test_engine.py        32 unit/property tests
├── tools/
│   ├── fuzz.py                 property-based checks on thousands of random scenarios
│   ├── sensitivity.py          one-input-at-a-time perturbation analysis
│   ├── make_edge_scenarios.py  regenerates scenarios/edge
│   └── package_submission.py   assembles the StackSense26_<Name>/ submission folder
└── report/
    ├── screenshots.py          captures real screenshots of the running UI (headless Edge/Chrome)
    └── build_report.py         builds Report_<Name>.pdf from live engine data and those screenshots
```

## 9. Validation evidence (reproducible)

```bash
python -m unittest discover -s tests       # 32 tests
python tools/fuzz.py 3000 2026             # 3,000 random scenarios: 0 invariant violations, ~5 ms each
python tools/sensitivity.py                # 128 single-input perturbations: avg 0.36 core decisions move
```

The fuzz harness re-checks every chosen component against the knowledge base independently of the engine:
no hard-constraint violation, no deprecated technology, budget overruns always flagged, determinism across
runs, no microservices for small teams, `ok` status never carries warnings.

### Rebuilding the report and the submission folder

```bash
python report/build_report.py          # screenshots + validation + report/build/Report_Kunal_Mittal.pdf
python tools/package_submission.py     # ../StackSense26_Kunal_Mittal/{source/, outputs/, Report_Kunal_Mittal.pdf}
```

## 10. Credits - third-party libraries, datasets and APIs

* **Runtime libraries:** none. Python standard library only. The UI uses no JavaScript libraries or web fonts.
* **Optional:** [`anthropic` Python SDK](https://github.com/anthropics/anthropic-sdk-python) (MIT) for the
  off-by-default description assistant; Claude API (Anthropic).
* **Container base image:** [`python:3.12-slim`](https://hub.docker.com/_/python).
* **Report tooling only (not needed to run the engine):** Microsoft Edge or Google Chrome (headless screenshots and
  PDF printing) and [Pillow](https://python-pillow.org/) for cropping screenshots.
* **Datasets / research sources:** Stack Overflow Developer Survey 2025, State of JavaScript 2024,
  TechEmpower Framework Benchmarks, DB-Engines ranking, CNCF survey reports, endoflife.date, and the official
  documentation, pricing, region and compliance pages of every technology in the knowledge base
  (285 links: `python stacksense.py kb --export kb.json` or the **Knowledge base** tab).
* **Regulations referenced:** RBI payment-data localisation circular (2018), DPDP Act 2023, CERT-In
  Directions (2022), GDPR, HIPAA, PCI DSS, ISO/IEC 27001, SOC 2.
* **AI assistance:** Claude Code (Anthropic) was used as a coding assistant while building this project;
  declared in the report's AI-assistance section.

## License

MIT - see [LICENSE](LICENSE).
