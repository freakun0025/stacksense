/* StackSense web UI - vanilla JS, no build step. Talks to the local Python API. */
"use strict";

const INR_PER_USD = 88; // display-only approximation
const GROUPS = [
  ["project", "Project"], ["scale", "Scale & traffic"], ["team", "Team"], ["budget", "Budget & timeline"],
  ["infrastructure", "Infrastructure & hard constraints"], ["requirements", "Functional requirements"],
  ["compliance", "Compliance"], ["priorities", "Priorities (1 = low, 5 = critical)"],
];
const SECTION_OF = { timeline: "budget" };
const S = { schema: null, scenarios: [], last: null, prev: null, kb: null, llm: null, validateTimer: null, loaded: {} };

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmtUsd = (n) => "$" + Number(n).toLocaleString("en-US");
const fmtInr = (n) => "₹" + Math.round(Number(n) * INR_PER_USD).toLocaleString("en-IN");

async function api(path, body) {
  const opts = body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
  const res = await fetch(path, opts);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}

function toast(msg) {
  const t = $("#toast");
  t.textContent = msg; t.hidden = false;
  clearTimeout(toast._t); toast._t = setTimeout(() => (t.hidden = true), 2200);
}

function switchTab(name) {
  $$(".tab").forEach((b) => b.classList.toggle("active", b.dataset.tab === name));
  $$(".tabpane").forEach((p) => p.classList.toggle("active", p.id === "tab-" + name));
  if (name === "kb" && !S.kb) loadKb();
}

/* ------------------------------------------------------------------ form */
function fieldControl(f) {
  const id = "f_" + f.path.replace(/\./g, "__");
  const def = f.default;
  if (f.kind === "enum") {
    const opts = (f.required ? [] : [`<option value="">(default${def !== null && def !== undefined ? ": " + esc(def) : ""})</option>`])
      .concat(f.enum.map((v) => `<option value="${esc(v)}">${esc(v)}</option>`));
    if (f.required) opts.unshift(`<option value="">— select —</option>`);
    return `<select id="${id}" data-path="${f.path}" data-kind="enum">${opts.join("")}</select>`;
  }
  if (f.kind === "list_enum") {
    return `<div class="multi" id="${id}" data-path="${f.path}" data-kind="list_enum">${f.enum
      .map((v) => `<label><input type="checkbox" value="${esc(v)}">${esc(v)}</label>`).join("")}</div>`;
  }
  if (f.kind === "list_str") {
    const dl = f.path === "team.languages" ? ` list="langs"` : "";
    return `<input type="text" id="${id}" data-path="${f.path}" data-kind="list_str"${dl} placeholder="comma-separated">`;
  }
  if (f.kind === "bool") {
    if (f.extra) {
      return `<select id="${id}" data-path="${f.path}" data-kind="tribool"><option value="">auto (inferred)</option><option value="true">yes</option><option value="false">no</option></select>`;
    }
    return `<label class="switch"><input type="checkbox" id="${id}" data-path="${f.path}" data-kind="bool"><span>${esc(f.label)}</span></label>`;
  }
  if (f.kind === "priority") {
    return `<div class="range-row"><input type="range" min="1" max="5" step="1" value="3" id="${id}" data-path="${f.path}" data-kind="priority"><span class="range-val">3</span></div>`;
  }
  if (f.kind === "int" || f.kind === "number" || f.kind === "int_or_null") {
    const step = f.kind === "number" ? "any" : "1";
    const ph = f.kind === "int_or_null" ? "empty = no target" : (f.required ? "required" : "optional");
    return `<input type="number" step="${step}" id="${id}" data-path="${f.path}" data-kind="${f.kind}" placeholder="${ph}">`;
  }
  if (f.path === "project.description") {
    return `<textarea id="${id}" data-path="${f.path}" data-kind="str" placeholder="Describe the product in a few sentences..."></textarea>`;
  }
  return `<input type="text" id="${id}" data-path="${f.path}" data-kind="str">`;
}

function fieldHtml(f) {
  const wide = ["project.description", "project.platforms", "compliance", "infrastructure.existing_systems",
    "scale.user_geography"].includes(f.path) || f.kind === "list_enum" ? " wide" : "";
  const name = f.kind === "bool" && !f.extra ? "" :
    `<label class="name" for="f_${f.path.replace(/\./g, "__")}">${esc(f.label)}${f.required ? ' <span class="req">*</span>' : ""}${f.extra ? ' <span class="badge extra">extra</span>' : ""} <span class="path">${esc(f.path)}</span></label>`;
  const affects = f.affects && f.affects.length ? ` <span class="path">→ ${esc(f.affects.join(", "))}</span>` : "";
  return `<div class="field${wide}" data-field="${f.path}">${name}${fieldControl(f)}<div class="help">${esc(f.help)}${affects}</div><div class="field-error"></div></div>`;
}

function buildForm(schema) {
  const root = $("#form-root");
  const byGroup = {};
  schema.fields.forEach((f) => {
    const g = f.extra ? "extra" : (SECTION_OF[f.group] || f.group);
    (byGroup[g] = byGroup[g] || []).push(f);
  });
  let html = "";
  GROUPS.concat([["extra", "StackSense extra parameters (optional)"]]).forEach(([g, title]) => {
    const fields = byGroup[g] || [];
    if (!fields.length) return;
    const req = fields.filter((f) => f.required).length;
    html += `<details class="section" ${g === "extra" ? "" : "open"} data-group="${g}"><summary>${esc(title)}<span class="count">${fields.length} fields${req ? ` · ${req} required` : ""}</span></summary><div class="section-body">${fields.map(fieldHtml).join("")}</div></details>`;
  });
  html += `<datalist id="langs">${schema.known_languages.map((l) => `<option value="${esc(l)}">`).join("")}</datalist>`;
  root.innerHTML = html;
  $$("input[type=range]", root).forEach((r) => r.addEventListener("input", () => (r.nextElementSibling.textContent = r.value)));
  const markDirty = (ev) => {
    const ctl = ev.target.closest("[data-path]");
    if (ctl) ctl.dataset.dirty = "1";
    scheduleValidate();
  };
  root.addEventListener("input", markDirty);
  root.addEventListener("change", markDirty);
}

function setPath(obj, path, value) {
  const parts = path.split(".");
  let cur = obj;
  for (let i = 0; i < parts.length - 1; i++) cur = cur[parts[i]] = cur[parts[i]] || {};
  cur[parts[parts.length - 1]] = value;
}
function getPath(obj, path) {
  return path.split(".").reduce((o, k) => (o && typeof o === "object" ? o[k] : undefined), obj);
}

/* A field is sent when the loaded scenario contained it, the user touched it, or it is required and filled.
   Untouched optional fields stay absent so the engine applies (and reports) its documented defaults - and a
   loaded scenario run from the UI produces the same input_hash as the CLI. */
function readForm() {
  const out = {};
  const sid = $("#scenario-id").value.trim();
  if (sid) out.scenario_id = sid;
  S.schema.fields.forEach((f) => {
    const el = document.getElementById("f_" + f.path.replace(/\./g, "__"));
    if (!el) return;
    const k = el.dataset.kind;
    const had = getPath(S.loaded, f.path) !== undefined;
    const dirty = el.dataset.dirty === "1";
    let v, empty = false;
    if (k === "enum") { v = el.value || undefined; empty = !el.value; }
    else if (k === "list_enum") { v = $$("input:checked", el).map((i) => i.value); empty = !v.length; }
    else if (k === "list_str") { const raw = el.value.trim(); v = raw ? raw.split(",").map((s) => s.trim()).filter(Boolean) : []; empty = !v.length; }
    else if (k === "bool") v = el.checked;
    else if (k === "tribool") { v = el.value ? el.value === "true" : undefined; empty = !el.value; }
    else if (k === "priority") v = Number(el.value);
    else if (k === "int" || k === "number") { v = el.value === "" ? undefined : Number(el.value); empty = el.value === ""; }
    else if (k === "int_or_null") { v = el.value === "" ? null : Number(el.value); empty = el.value === ""; }
    else if (k === "str") { v = el.value; empty = !el.value.trim(); }
    let include;
    if (had) include = !(empty && (k === "enum" || k === "tribool" || k === "int" || k === "number"));
    else if (dirty) include = !empty || k === "list_enum" || k === "list_str";
    else include = f.required && !empty;
    if (include && v !== undefined) setPath(out, f.path, v);
  });
  return out;
}

function writeForm(data, keepLoaded) {
  if (!keepLoaded) S.loaded = JSON.parse(JSON.stringify(data || {}));
  $("#scenario-id").value = data && data.scenario_id ? data.scenario_id : "";
  S.schema.fields.forEach((f) => {
    const el = document.getElementById("f_" + f.path.replace(/\./g, "__"));
    if (!el) return;
    if (!keepLoaded) delete el.dataset.dirty;
    const v = getPath(data || {}, f.path);
    const k = el.dataset.kind;
    if (k === "enum") el.value = typeof v === "string" && f.enum.includes(v) ? v : "";
    else if (k === "list_enum") $$("input", el).forEach((i) => (i.checked = Array.isArray(v) && v.includes(i.value)));
    else if (k === "list_str") el.value = Array.isArray(v) ? v.join(", ") : "";
    else if (k === "bool") el.checked = v === true;
    else if (k === "tribool") el.value = v === true ? "true" : v === false ? "false" : "";
    else if (k === "priority") { el.value = Number.isInteger(v) && v >= 1 && v <= 5 ? v : 3; el.nextElementSibling.textContent = el.value; }
    else if (k === "int" || k === "number" || k === "int_or_null") el.value = typeof v === "number" ? v : "";
    else if (k === "str") el.value = typeof v === "string" ? v : "";
  });
  scheduleValidate();
}

function scheduleValidate() {
  clearTimeout(S.validateTimer);
  S.validateTimer = setTimeout(runValidate, 250);
}
async function runValidate() {
  const lenient = $("#lenient").checked ? "?lenient=1" : "";
  try {
    const v = await api("/api/validate" + lenient, readForm());
    $$(".field").forEach((el) => { el.classList.remove("has-error"); $(".field-error", el).textContent = ""; });
    v.validation_errors.forEach((e) => {
      const el = document.querySelector(`.field[data-field="${CSS.escape(e.field)}"]`);
      if (el) { el.classList.add("has-error"); $(".field-error", el).textContent = e.message; }
    });
    const box = $("#validation-box");
    box.innerHTML = v.valid
      ? `<div class="ok">✓ Input is valid${v.assumptions.length ? ` · ${v.assumptions.length} default(s) will be applied` : ""}</div>`
      : `<div><b>${v.validation_errors.length} field error(s)</b><ul>${v.validation_errors.map((e) => `<li><code>${esc(e.field)}</code> ${esc(e.message)}</li>`).join("")}</ul></div>`;
  } catch (e) { /* server not reachable */ }
}

/* ------------------------------------------------------------------ description assistant */
async function suggest(useLlm) {
  const text = (getPath(readForm(), "project.description") || "").trim();
  const box = $("#suggest-box");
  if (!text) { box.innerHTML = `<p class="muted small">Write a description first.</p>`; return; }
  box.innerHTML = `<span class="spinner"></span>`;
  const res = await api("/api/describe", { text, use_llm: !!useLlm });
  let items = res.suggestions.map((s) => ({ ...s, source: "rules" }));
  if (res.llm) items = items.concat(res.llm.suggestions || []);
  const sig = Object.entries(res.signals || {});
  box.innerHTML = (items.length ? items.map((s, i) => `<div class="suggestion"><div class="s-body"><code>${esc(s.field)}</code> → <b>${esc(JSON.stringify(s.value))}</b><div class="muted">“${esc(s.evidence)}” · ${esc(s.reason)} <span class="badge">${esc(s.source)}</span></div></div><button class="btn btn-ghost" data-apply="${i}">Apply</button></div>`).join("") : `<p class="muted small">No structured hints found.</p>`)
    + (sig.length ? `<div class="sub-h">Engine signals</div>${sig.map(([k, v]) => `<div class="small">• <b>${esc(k)}</b>: ${esc(v.meaning)} <span class="muted">(“${esc(v.evidence)}”)</span></div>`).join("")}` : "")
    + (res.llm && res.llm.error ? `<p class="small muted">${esc(res.llm.error)}</p>` : "");
  $$("[data-apply]", box).forEach((b) => b.addEventListener("click", () => {
    const s = items[Number(b.dataset.apply)];
    const data = readForm();
    const spec = S.schema.fields.find((f) => f.path === s.field);
    if (spec && spec.kind === "list_enum") {
      const cur = getPath(data, s.field) || [];
      if (!cur.includes(s.value)) cur.push(s.value);
      setPath(data, s.field, cur);
    } else setPath(data, s.field, s.value);
    writeForm(data, true);
    const ctl = document.getElementById("f_" + s.field.replace(/\./g, "__"));
    if (ctl) ctl.dataset.dirty = "1";
    b.textContent = "✓"; b.disabled = true;
  }));
}

/* ------------------------------------------------------------------ run + render */
async function run() {
  const btn = $("#btn-run");
  btn.innerHTML = `<span class="spinner"></span> Thinking…`;
  try {
    const lenient = $("#lenient").checked ? "?lenient=1" : "";
    const r = await api("/api/recommend" + lenient, readForm());
    S.prev = S.last; S.last = r;
    renderResult(r, S.prev);
    switchTab("result");
    window.scrollTo(0, 0);
  } catch (e) { toast("Error: " + e.message); }
  btn.innerHTML = "Recommend stack →";
}

function compCard(layer, c, prevC) {
  if (!c) return "";
  const changed = prevC && prevC.choice !== c.choice;
  const none = c.choice === "None";
  const alts = (c.alternatives || []).map((a) => `<div class="alt"><b>${esc(a.choice)}</b>${esc(a.why_not)}</div>`).join("");
  const trades = (c.tradeoffs || []).length ? `<ul class="trade">${c.tradeoffs.map((t) => `<li>${esc(t)}</li>`).join("")}</ul>` : `<p class="muted small">None significant.</p>`;
  const srcs = (c.sources || []).length ? `<div class="srcs">Sources: ${c.sources.map((u) => `<a href="${esc(u)}" target="_blank" rel="noopener">${esc(u.replace(/^https?:\/\//, ""))}</a>`).join(" · ")}</div>` : "";
  const conf = c.confidence ? `<span class="conf conf-${c.confidence}">${c.confidence === "low" ? "close call" : c.confidence + " confidence"}</span>` : "";
  return `<div class="comp${changed ? " changed" : ""}" data-layer="${esc(layer)}">
    <div class="comp-layer">${esc(layer)}${c.purpose ? ` · <span style="text-transform:none">${esc(c.purpose)}</span>` : ""}${conf}</div>
    ${changed ? `<div class="chg-tag">CHANGED · was ${esc(prevC.choice)}</div>` : ""}
    <div class="comp-choice${none ? " none" : ""}">${esc(c.choice)}</div>
    ${c.version ? `<div class="small muted">${esc(c.version)}</div>` : ""}
    <p class="just">${esc(c.justification)}</p>
    <div class="drivers">${(c.driven_by || []).map((d) => `<span class="driver">${esc(d)}</span>`).join("")}</div>
    <div class="sub-h">Alternatives considered</div>${alts || `<p class="muted small">—</p>`}
    <div class="sub-h">Trade-offs</div>${trades}${srcs}
  </div>`;
}

function suppCard(c, prevMap) {
  const key = c.layer + "|" + (c.purpose || "");
  const prevC = prevMap ? prevMap[key] : null;
  const changed = prevMap && (!prevC || prevC.choice !== c.choice);
  return `<div class="comp supp${changed ? " changed" : ""}">
    <div class="comp-layer">${esc(c.layer)}${c.purpose ? ` · <span style="text-transform:none">${esc(c.purpose)}</span>` : ""}<span class="conf conf-${c.confidence}">${c.confidence === "low" ? "close call" : c.confidence}</span></div>
    ${changed ? `<div class="chg-tag">${prevC ? "CHANGED · was " + esc(prevC.choice) : "NEW"}</div>` : ""}
    <div class="comp-choice" style="font-size:15px">${esc(c.choice)}</div>
    <p class="just">${esc(c.justification)}</p>
    <div class="drivers">${(c.driven_by || []).slice(0, 5).map((d) => `<span class="driver">${esc(d)}</span>`).join("")}</div>
    <details><summary>Alternatives & trade-offs</summary>
      ${(c.alternatives || []).map((a) => `<div class="alt"><b>${esc(a.choice)}</b>${esc(a.why_not)}</div>`).join("") || '<p class="muted small">—</p>'}
      ${(c.tradeoffs || []).length ? `<ul class="trade">${c.tradeoffs.map((t) => `<li>${esc(t)}</li>`).join("")}</ul>` : ""}
    </details></div>`;
}

function traceTable(rows) {
  if (!rows || !rows.length) return `<p class="muted small">Not applicable.</p>`;
  const max = Math.max(...rows.filter((r) => r.score !== null).map((r) => r.score), 1);
  return `<table><thead><tr><th>Candidate</th><th style="width:110px">Fit score</th><th>Top factors / exclusion reason</th></tr></thead><tbody>${rows.map((r) => `
    <tr class="${r.status === "selected" ? "sel" : r.status === "excluded" ? "exc" : ""}"><td><b>${esc(r.choice)}</b><div class="small muted">${esc(r.status)}</div></td>
    <td>${r.score === null ? "—" : `${r.score.toFixed(2)}<div class="score-bar" style="width:${Math.max(4, (Math.max(r.score, 0) / max) * 100)}%"></div>`}</td>
    <td class="small">${r.reason ? "✗ " + esc(r.reason) : (r.top_factors || []).map(esc).join("<br>")}</td></tr>`).join("")}</tbody></table>`;
}

function renderResult(r, prev) {
  $("#result-empty").hidden = true;
  const root = $("#result-root");
  root.hidden = false;
  const c = r.estimated_monthly_cost_usd || { min: 0, max: 0, assumptions: [] };
  const budget = getPath(readForm(), "budget.monthly_infra_usd");
  const st = r.status;
  const warns = r.warnings || [];
  const counts = { critical: 0, warning: 0, info: 0 };
  warns.forEach((w) => counts[w.severity]++);
  let html = `<div class="result-actions">
      <button class="btn" id="btn-dl">Download JSON</button><button class="btn" id="btn-copy">Copy JSON</button>
      <button class="btn btn-ghost" id="btn-edit">← Edit inputs (what-if)</button></div>
    <div class="status-banner" id="sec-summary"><span class="status-pill st-${esc(st)}">${esc(st.replace(/_/g, " "))}</span>
      <div><div class="summary">${esc(r.summary)}</div>
      <div class="meta-line"><span class="chip">scenario ${esc(r.scenario_id || "—")}</span><span class="chip">engine ${esc(r.engine_version)}</span>
      <span class="chip">KB ${esc(r.kb_version || "")}</span><span class="chip mono">input_hash ${esc(r.input_hash || "")}</span>
      <span class="chip chip-ok">LLM used: ${r.llm_used ? "yes" : "no"}</span>
      <span class="chip">${counts.critical} critical · ${counts.warning} warning · ${counts.info} info</span></div></div></div>`;

  if (prev && prev.stack && r.stack) {
    const diffs = [];
    ["frontend", "backend", "database", "hosting"].forEach((k) => {
      if (prev.stack[k].choice !== r.stack[k].choice) diffs.push(`<li><b>${k}</b>: ${esc(prev.stack[k].choice)} → <b>${esc(r.stack[k].choice)}</b></li>`);
    });
    if (prev.architecture_style !== r.architecture_style) diffs.push(`<li><b>architecture</b>: ${esc(prev.architecture_style)} → <b>${esc(r.architecture_style)}</b></li>`);
    const pm = Object.fromEntries((prev.stack.supporting || []).map((s) => [s.layer + "|" + (s.purpose || ""), s.choice]));
    (r.stack.supporting || []).forEach((s) => { const k = s.layer + "|" + (s.purpose || ""); if (pm[k] !== s.choice) diffs.push(`<li><b>${esc(s.layer)}${s.purpose ? " (" + esc(s.purpose) + ")" : ""}</b>: ${esc(pm[k] || "—")} → <b>${esc(s.choice)}</b></li>`); });
    html += `<div class="card diff-box"><h3>What changed since the previous run</h3>${diffs.length ? `<ul>${diffs.join("")}</ul>` : `<p class="muted">Same stack - the input change did not move any decision (stable output).</p>`}
      <p class="small muted">Cost: ${fmtUsd(prev.estimated_monthly_cost_usd.min)}–${fmtUsd(prev.estimated_monthly_cost_usd.max)} → ${fmtUsd(c.min)}–${fmtUsd(c.max)}</p></div>`;
  }

  if ((r.validation_errors || []).length) {
    html += `<div class="card"><h3>Validation errors</h3><table><thead><tr><th>Field</th><th>Problem</th></tr></thead><tbody>${r.validation_errors.map((e) => `<tr><td class="mono">${esc(e.field)}</td><td>${esc(e.message)}</td></tr>`).join("")}</tbody></table></div>`;
  }
  if (r.resolution_options) {
    html += `<div class="card"><h3>How to resolve</h3><ul>${r.resolution_options.map((o) => `<li>${esc(o)}</li>`).join("")}</ul></div>`;
  }

  if (r.stack) {
    const lo = c.min, hi = c.max, scale = Math.max(hi, budget || 0, 1) * 1.1;
    html += `<div class="kpis" id="sec-kpis">
      <div class="card"><div class="kpi-label">Architecture style</div><div class="arch-style">${esc(r.architecture_style.replace(/_/g, " "))}</div>
        <div class="kpi-sub">${esc(r.architecture_rationale ? r.architecture_rationale.text : "")}</div></div>
      <div class="card" id="sec-cost"><div class="kpi-label">Estimated monthly cost</div><div class="kpi-value">${fmtUsd(lo)} – ${fmtUsd(hi)}</div>
        <div class="kpi-sub">≈ ${fmtInr(lo)} – ${fmtInr(hi)} (at ₹${INR_PER_USD}/US$) · budget ${budget !== undefined ? fmtUsd(budget) : "—"}</div>
        <div class="budget-bar"><div class="band" style="left:${(lo / scale) * 100}%;width:${Math.max(1, ((hi - lo) / scale) * 100)}%"></div>${budget !== undefined ? `<div class="budget" style="left:${(budget / scale) * 100}%" title="budget"></div>` : ""}</div>
        <details><summary class="small">Breakdown & assumptions</summary><table><tbody>${(c.breakdown || []).map((b) => `<tr><td>${esc(b.component)}<div class="small muted">${esc(b.basis)}</div></td><td class="mono">${fmtUsd(Math.round(b.min))}–${fmtUsd(Math.round(b.max))}</td></tr>`).join("")}</tbody></table>
        <ul class="small">${(c.assumptions || []).map((a) => `<li>${esc(a)}</li>`).join("")}</ul></details></div>
      <div class="card"><div class="kpi-label">Profile</div>${r.profile ? `<div class="small">
        <div>Scale tier <b>${esc(r.profile.scale_tier)}</b> · ${Number(r.profile.users_design_target).toLocaleString()} users · ${Number(r.profile.peak_concurrent_users).toLocaleString()} concurrent · ~${Number(r.profile.peak_rps_estimate).toLocaleString()} req/s</div>
        <div>Data ${esc(r.profile.db_gb)} GB DB + ${esc(r.profile.media_gb)} GB media</div>
        <div>Region <b>${esc(r.profile.primary_region)}</b> · residency <b>${esc(r.profile.effective_residency)}</b></div>
        <div>Effort ${esc(r.profile.feature_points)} pts vs capacity ${esc(r.profile.team_capacity)} (ratio ${esc(r.profile.effort_ratio)})</div>
        ${(r.profile.description_signals || []).length ? `<div>Description signals: ${r.profile.description_signals.map((s) => `<span class="driver">${esc(s)}</span>`).join(" ")}</div>` : ""}</div>` : ""}</div>
    </div>`;
    html += `<h3 id="sec-core">Core stack</h3><div class="core-grid">${["frontend", "backend", "database", "hosting"].map((k) => compCard(k, r.stack[k], prev && prev.stack ? prev.stack[k] : null)).join("")}</div>`;
    const pmap = prev && prev.stack ? Object.fromEntries((prev.stack.supporting || []).map((s) => [s.layer + "|" + (s.purpose || ""), s])) : null;
    html += `<h3 id="sec-support">Supporting services (${r.stack.supporting.length})</h3><div class="supp-grid">${r.stack.supporting.map((s) => suppCard(s, pmap)).join("")}</div><br>`;
  }

  html += `<div class="grid2"><div class="card" id="sec-warnings"><h3>Warnings &amp; risks (${warns.length})</h3>${warns.length ? warns.map((w) => `<div class="warn sev-${w.severity}"><span class="sev">${esc(w.severity)}</span><div><b>${esc(w.code)}</b> — ${esc(w.message)}<div><code>${esc((w.fields || []).join(", "))}</code></div></div></div>`).join("") : `<p class="muted">None.</p>`}</div>
    <div class="card" id="sec-assumptions"><h3>Assumptions &amp; relaxations (${(r.assumptions || []).length})</h3><ul class="assume">${(r.assumptions || []).map((a) => `<li class="${a.startsWith("RELAXED") ? "relaxed" : ""}">${esc(a)}</li>`).join("") || "<li class='muted'>None.</li>"}</ul></div></div>`;

  if (r.decision_trace) {
    html += `<div class="card" id="sec-trace"><h3>Decision trace (how each layer was scored)</h3>${Object.entries(r.decision_trace).map(([k, rows]) => `<details ${k === "backend" ? "open" : ""}><summary><b>${esc(k)}</b></summary><div class="table-wrap">${traceTable(rows)}</div></details>`).join("")}</div>`;
  }
  root.innerHTML = html;
  $("#btn-dl").onclick = () => {
    const blob = new Blob([JSON.stringify(r, null, 2) + "\n"], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = `${r.scenario_id || "stacksense"}_output.json`; a.click();
  };
  $("#btn-copy").onclick = async () => { await navigator.clipboard.writeText(JSON.stringify(r, null, 2)); toast("Copied JSON"); };
  $("#btn-edit").onclick = () => switchTab("configure");
}

/* ------------------------------------------------------------------ knowledge base */
async function loadKb() {
  S.kb = await api("/api/kb");
  const layers = [...new Set(S.kb.technologies.map((t) => t.layer))].sort();
  $("#kb-layer").innerHTML = `<option value="">All layers</option>` + layers.map((l) => `<option>${esc(l)}</option>`).join("");
  const active = S.kb.technologies.filter((t) => t.status === "active").length;
  $("#kb-meta").textContent = `${S.kb.technologies.length} entries (${active} active) · ${S.kb.lifecycle.length} lifecycle records · ${S.kb.sources.length} cited sources · snapshot ${S.kb.as_of}`;
  renderKb();
  $("#life-table").innerHTML = `<thead><tr><th>Technology</th><th>Status</th><th>Date</th><th>Replace with</th></tr></thead><tbody>${S.kb.lifecycle.map((l) => `<tr><td>${esc(l.name)}<div class="small muted">${esc(l.note || "")}</div></td><td class="status-${l.kind === "eol" ? "eol" : "maintenance"}">${esc(l.kind)}</td><td class="mono">${esc(l.date)}</td><td>${esc(l.replacement)}</td></tr>`).join("")}</tbody>`;
  $("#sources-list").innerHTML = S.kb.sources.map((s) => `<div><span class="badge">${esc(s.type)}</span> <a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)}</a></div>`).join("");
}
function renderKb() {
  const q = $("#kb-search").value.trim().toLowerCase();
  const layer = $("#kb-layer").value;
  const inactive = $("#kb-inactive").checked;
  const rows = S.kb.technologies.filter((t) => (inactive || t.status === "active") && (!layer || t.layer === layer)
    && (!q || JSON.stringify([t.name, t.id, t.kind, t.traits, t.regions, t.compliance, t.langs]).toLowerCase().includes(q)));
  $("#kb-table").innerHTML = `<thead><tr><th>Technology</th><th>Layer</th><th>Status</th><th>Perf/Scale/TTM/Maint/Cost/Sec</th><th>Learn/Ops</th><th>Regions</th><th>Compliance</th><th>Languages</th></tr></thead><tbody>${rows.map((t) => `
    <tr><td><b>${esc(t.name)}</b><div class="small muted">${esc(t.kind)}</div></td><td>${esc(t.layer)}</td>
    <td class="status-${esc(t.status)}">${esc(t.status)}${t.status_note ? `<div class="small">${esc(t.status_note)}</div>` : ""}</td>
    <td class="sc">${Object.values(t.scores).join(" / ")}</td><td class="sc">${t.learn} / ${t.ops}</td>
    <td class="small">${esc((t.regions || []).join(", ") || "global")}</td><td class="small">${esc((t.compliance || []).join(", "))}</td>
    <td class="small">${esc((t.langs || []).join(", "))}</td></tr>`).join("")}</tbody>`;
}

/* ------------------------------------------------------------------ boot */
async function loadScenario(id) {
  const s = S.scenarios.find((x) => x.id === id);
  if (!s) return false;
  writeForm(s.data);
  S.prev = null; S.last = null;
  return true;
}

async function boot() {
  $$(".tab").forEach((b) => b.addEventListener("click", () => switchTab(b.dataset.tab)));
  const [schema, scenarios, health] = await Promise.all([api("/api/schema"), api("/api/scenarios"), api("/api/health")]);
  S.schema = schema; S.scenarios = scenarios; S.llm = health.llm;
  buildForm(schema);
  const sel = $("#scenario-select");
  const grp = (g, label) => `<optgroup label="${label}">${scenarios.filter((s) => s.group === g).map((s) => `<option value="${esc(s.id)}">${esc(s.id)}${s.name ? " — " + esc(s.name) : ""}</option>`).join("")}</optgroup>`;
  sel.innerHTML = `<option value="">— choose —</option>` + grp("public", "Public scenarios (Appendix A)") + grp("edge", "Edge cases");
  sel.addEventListener("change", () => { if (sel.value) { loadScenario(sel.value); toast("Loaded " + sel.value); } });
  $("#llm-chip").textContent = health.llm.enabled ? "LLM: suggestions only" : "LLM: off";
  $("#llm-chip").title = health.llm.message;
  $("#llm-chip").classList.add(health.llm.enabled ? "chip" : "chip-off");
  $("#btn-suggest-ai").hidden = !health.llm.enabled;
  $("#btn-run").addEventListener("click", run);
  $("#btn-suggest").addEventListener("click", () => suggest(false));
  $("#btn-suggest-ai").addEventListener("click", () => suggest(true));
  $("#btn-reset").addEventListener("click", () => { writeForm({}); sel.value = ""; S.prev = null; });
  $("#lenient").addEventListener("change", scheduleValidate);
  $("#btn-export-input").addEventListener("click", () => {
    const blob = new Blob([JSON.stringify(readForm(), null, 2)], { type: "application/json" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "scenario_input.json"; a.click();
  });
  $("#file-input").addEventListener("change", async (ev) => {
    const f = ev.target.files[0]; if (!f) return;
    try {
      let data = JSON.parse(await f.text());
      if (Array.isArray(data)) data = data[0];
      writeForm(data); S.prev = null; toast("Imported " + f.name);
    } catch (e) { toast("Invalid JSON file: " + e.message); }
    ev.target.value = "";
  });
  ["#kb-search", "#kb-layer", "#kb-inactive"].forEach((s) => $(s).addEventListener("input", () => S.kb && renderKb()));
  writeForm({});

  // deep links, e.g. ?scenario=P2&run=1&focus=sec-core  (used for documentation screenshots)
  const qp = new URLSearchParams(location.search);
  const theme = qp.get("theme") || (() => { try { return localStorage.getItem("ss-theme"); } catch (e) { return null; } })();
  if (theme) document.documentElement.dataset.theme = theme;
  $("#theme-toggle").addEventListener("click", () => {
    const dark = document.documentElement.dataset.theme === "dark" ||
      (!document.documentElement.dataset.theme && matchMedia("(prefers-color-scheme: dark)").matches);
    document.documentElement.dataset.theme = dark ? "light" : "dark";
    try { localStorage.setItem("ss-theme", document.documentElement.dataset.theme); } catch (e) { /* ignore */ }
  });
  if (qp.get("scenario")) { sel.value = qp.get("scenario"); await loadScenario(qp.get("scenario")); }
  if (qp.get("tab")) switchTab(qp.get("tab"));
  if (qp.get("run") === "1") await run();
  if (qp.get("open")) $$("details").forEach((d) => (d.open = qp.get("open") === "all" || d.closest("#" + qp.get("open"))));
  if (qp.get("focus")) {
    const el = document.getElementById(qp.get("focus"));
    if (el) { const y = el.getBoundingClientRect().top + window.scrollY - 70; window.scrollTo(0, y); }
  }
  document.body.dataset.ready = "1";
}
boot().catch((e) => { document.body.innerHTML = `<pre style="padding:20px">StackSense UI failed to start: ${esc(e.message)}\nIs the server running? (python stacksense.py serve)</pre>`; });
