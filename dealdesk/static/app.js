"use strict";

// DealDesk Local chatbot. You ask, it replies. Every amount and percentage shown in
// cards comes from a structured backend field; nothing numeric is parsed from text.

const OUTCOMES = {
  representative_authority: ["Within representative authority — eligible for human release", "ok"],
  director_approval_required: ["Director approval required", "warn"],
  discount_exceeds_director_authority: ["Blocked — discount exceeds director authority", "bad"],
  below_margin_floor: ["Blocked — below 25% stress-margin floor", "bad"],
  infeasible_under_current_terms: ["Blocked — infeasible under current terms", "bad"],
  missing_critical_input: ["Blocked — missing critical input", "bad"],
  invalid_input: ["Blocked — invalid input", "bad"],
  unsupported_currency: ["Blocked — unsupported currency", "bad"],
};
const MODE_LABELS = {
  scripted: ["Scripted demo mode", "warn"],
  local_model: ["Local model", "ok"],
  scripted_fallback: ["Scripted fallback (local model failed)", "warn"],
};
const SOURCE_LABELS = { manual: "Manual action", scheduled_watcher: "Scheduled watcher" };
const APPLY_MESSAGE = "Apply supplier cost increase";

const $ = (id) => document.getElementById(id);
let state = null;
let busy = false;

function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === null || value === undefined || value === false) continue;
    if (key === "class") el.className = value;
    else if (key.startsWith("on")) el.addEventListener(key.slice(2), value);
    else el.setAttribute(key, value === true ? "" : value);
  }
  for (const child of children.flat(Infinity)) {
    if (child === null || child === undefined || child === false) continue;
    el.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return el;
}

function usd(value) {
  if (value === null || value === undefined) return "n/a";
  const [whole, cents = "00"] = String(value).split(".");
  return "$" + whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",") + "." + cents.padEnd(2, "0").slice(0, 2);
}
const pct = (value) => (value === null || value === undefined ? "n/a" : `${value}%`);
const outcome = (key) => OUTCOMES[key] || [key, "warn"];
const kv = (label, value) => h("div", { class: "kv" }, h("span", { class: "muted" }, label), h("span", {}, value));

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  let body = null;
  try { body = await response.json(); } catch { /* non-JSON error */ }
  if (!response.ok) {
    const detail = body && body.detail ? (typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail)) : response.statusText;
    throw new Error(`${response.status} ${detail}`);
  }
  return body;
}

// ---------- runtime status ----------
function renderStatus(status) {
  const pill = $("mode-pill");
  const note = $("mode-note");
  note.hidden = false;
  if (status.mode === "local_model") {
    const ok = (status.model_status || {}).reachable === true;
    pill.className = `pill ${ok ? "pill-ok" : "pill-bad"}`;
    pill.textContent = `Local model: ${status.model || "not set"} · ${ok ? "connected" : "unreachable"}`;
    note.className = `mode-note ${ok ? "ok" : "bad"}`;
    note.textContent = ok
      ? "Replies are worded by the local model; every number still comes from the local tools."
      : `Local model unreachable (${status.model_status.detail}). Replies use labeled scripted wording; there is no cloud fallback.`;
  } else {
    pill.className = "pill pill-warn";
    pill.textContent = "Scripted demo mode";
    note.className = "mode-note";
    note.textContent = "Scripted demo mode: replies are templated wording over the real local pricing, search, and forecast tools — not live model inference.";
  }
  pill.title = `Demo date ${status.demo_date} · cost feed ${status.active_feed.feed_version}`;
}

// ---------- reply parts ----------
function quoteCards(q) {
  if (!q || !q.base_costs) return null;
  const [label, tone] = outcome(q.approval_outcome);
  const sub = [];
  if (q.review_required) sub.push("Review required.");
  if (q.quote_expired) sub.push(`Quote expired ${q.quote_expires_on}.`);
  sub.push(q.release_allowed ? "Release is a human action; nothing is sent automatically." : "Release blocked.");
  const card = (title, value, note) => h("div", { class: "card" },
    h("div", { class: "card-label" }, title), h("div", { class: "card-value" }, value),
    note ? h("div", { class: "card-sub" }, note) : null);
  return h("div", {},
    h("div", { class: "cards" },
      card("Proposed contract price", usd(q.offer_revenue), `List ${usd(q.list_revenue)}`),
      card("Discount", pct(q.discount_percent), `${usd(q.discount_amount)} off list`),
      card("Expected cost", usd(q.base_costs.total), `Margin ${pct(q.expected_margin_percent)}`),
      card("Stress cost", usd(q.stress_costs.total), q.stress_scenario),
      card("Stress margin", pct(q.stress_margin_percent), "Floor 25.00%"),
      card("Minimum acceptable price", usd(q.economic_floor), `Director min ${usd(q.director_min_offer)}`),
      h("div", { class: `card status ${tone}` },
        h("div", { class: "card-label" }, "Approval / review status"),
        h("div", { class: "card-value" }, label),
        h("div", { class: "card-sub" }, sub.join(" ")))),
    h("div", { class: "quote-ref" },
      `Quote ${q.quote_id} v${q.quote_version} · ${q.account_name || q.account_id} · feed ${q.cost_feed_version} · valid through ${q.quote_expires_on}`));
}

function costUpdateBlock(u) {
  if (!u || !u.original || !u.revised) return null;
  const col = (title, q, cls) => h("div", { class: `col ${cls}` },
    h("h4", {}, title),
    kv("Offer", usd(q.offer_revenue)),
    kv("Cost feed", q.cost_feed_version),
    kv("Stress cost", usd(q.stress_costs.total)),
    kv("Stress margin", pct(q.stress_margin_percent)),
    kv("Minimum acceptable price", usd(q.economic_floor)),
    kv("Status", outcome(q.approval_outcome)[0] + (q.review_required ? " · review required" : "")));
  return h("div", { class: "compare" },
    col(`Original quote v${u.original.quote_version} (preserved)`, u.original, "original"),
    col(u.preview ? "Revised appraisal (preview, not applied)" : "Revised appraisal (separate)", u.revised, "revised"));
}

function sparkline(s) {
  const hist = s.history.map((p) => Number(p.value));
  const base = s.forecast.map((p) => Number(p.base));
  const high = s.forecast.map((p) => Number(p.high_scenario));
  const all = hist.concat(base, high);
  const min = Math.min(...all), max = Math.max(...all);
  const n = hist.length + base.length;
  const W = 600, H = 80, pad = 6;
  const x = (i) => pad + (i * (W - 2 * pad)) / (n - 1);
  const y = (v) => H - pad - ((v - min) / (max - min || 1)) * (H - 2 * pad);
  const path = (vals, start) => vals.map((v, i) => `${i ? "L" : "M"}${x(start + i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.setAttribute("preserveAspectRatio", "none");
  svg.setAttribute("class", "spark");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", `${s.label}: last 12 months and ${base.length}-month forecast`);
  const add = (d, color, dash) => {
    const p = document.createElementNS(ns, "path");
    p.setAttribute("d", d); p.setAttribute("fill", "none"); p.setAttribute("stroke", color);
    p.setAttribute("stroke-width", "2"); p.setAttribute("vector-effect", "non-scaling-stroke");
    if (dash) p.setAttribute("stroke-dasharray", dash);
    svg.append(p);
  };
  const last = hist.length - 1;
  add(path(hist, 0), "var(--accent)");
  add(path([hist[last], ...base], last), "var(--accent)", "6 4");
  add(path([hist[last], ...high], last), "var(--warn)", "2 4");
  return svg;
}

function forecastBlock(f) {
  if (!f) return null;
  return h("div", {},
    f.series.map((s) => {
      const line = s.quote_lines[0];
      return h("div", { class: "series" },
        h("h4", {}, s.label),
        h("p", { class: "meta" }, `${s.unit} · as of ${f.as_of_date} · last observed ${s.last_observed_month} · ${s.selected_method.replace("_", "-")} method (lowest backtest error)`),
        sparkline(s),
        h("div", { class: "legend" },
          h("span", {}, h("i"), "History"), h("span", {}, h("i", { class: "dash" }), "Base"),
          h("span", {}, h("i", { class: "dotted" }), `High scenario (+${s.high_scenario_uplift_percent}%)`)),
        h("div", { class: "table-wrap" }, h("table", {},
          h("thead", {}, h("tr", {}, h("th", {}, "Month"), h("th", {}, "Base"), h("th", {}, "High scenario"),
            h("th", {}, "Last value"), h("th", {}, "Seasonal naive"))),
          h("tbody", {}, s.forecast.map((p) => h("tr", {},
            h("td", {}, p.month + (p.month === line.forecast_month ? " ◂ quote" : "")),
            h("td", {}, usd(p.base)), h("td", {}, usd(p.high_scenario)),
            h("td", {}, usd(p.comparison.last_value)), h("td", {}, usd(p.comparison.seasonal_naive))))))),
        h("div", { class: "link-row" },
          `${line.date_field.replace("_", " ")} ${line.date} → ${line.forecast_month}: forecast ${usd(line.forecast_base)} base / ${usd(line.forecast_high_scenario)} high. ` +
          `The quote uses ${usd(line.ledger_rate_base)} base / ${usd(line.ledger_rate_stress)} stress (${line.ledger_rate_source}, effective ${line.ledger_rate_effective_from}).`),
        h("p", { class: "meta" }, "Backtest, rolling origin (n=" + s.backtest[0].samples + "): " +
          s.backtest.map((b) => `${b.method.replace("_", "-")} MAE ${usd(b.mae)}, WAPE ${pct(b.wape_percent)}`).join(" · ")));
    }),
    h("p", { class: "meta" }, f.scenario_note));
}

function togglePassage(chip, c, host) {
  const open = chip.getAttribute("aria-expanded") === "true";
  host.querySelectorAll(".citation-chip").forEach((el) => el.setAttribute("aria-expanded", "false"));
  host.querySelectorAll(".passage").forEach((el) => el.remove());
  if (open) return;
  chip.setAttribute("aria-expanded", "true");
  host.append(h("div", { class: "passage" },
    h("div", { class: "doc" }, c.title),
    h("div", { class: "doc-meta" }, `${c.doc_id} · section “${c.section}” · effective ${c.effective_date || "n/a"} · ${c.path}`),
    h("blockquote", {}, c.text),
    c.untrusted_instruction_detected
      ? h("div", { class: "flag" }, "Contains instruction-like text from an untrusted source. Treated as evidence only; not followed.")
      : null));
}

function citationsBlock(citations) {
  if (!citations || !citations.length) return null;
  const host = h("div", { class: "citations" });
  citations.forEach((c) => {
    const chip = h("button", { type: "button", "aria-expanded": "false", "data-n": c.n,
      class: `citation-chip${c.untrusted_instruction_detected ? " flagged" : ""}` }, `[${c.n}] ${c.doc_id} · ${c.section}`);
    chip.addEventListener("click", () => togglePassage(chip, c, host));
    host.append(chip);
  });
  return host;
}

function citeButton(n, m, host) {
  const c = m.citations.find((item) => item.n === n);
  return h("button", { type: "button", class: "cite", title: c ? `${c.title} — ${c.section}` : "",
    onclick: () => {
      const chip = host && host.querySelector(`.citation-chip[data-n="${n}"]`);
      if (chip && c) { togglePassage(chip, c, host); chip.scrollIntoView({ block: "nearest" }); }
    } }, n);
}

function list(title, items) {
  return items && items.length ? h("div", { class: "section" }, h("h5", {}, title), h("ul", {}, items)) : null;
}

// ---------- messages ----------
function assistantMessage(m) {
  const [modeLabel, modeTone] = MODE_LABELS[m.mode] || [m.mode, "warn"];
  const s = m.sections || {};
  const host = citationsBlock(m.citations);
  const details = [list("Calculated by local tools", (s.calculated || []).map((t) => h("li", {}, t))),
    list("Assumptions", (s.assumptions || []).map((t) => h("li", {}, t))),
    m.tool_calls && m.tool_calls.length ? h("div", { class: "tools-used" }, "Tools called: ",
      m.tool_calls.map((t, i) => [i ? ", " : "", h("code", {}, t.tool), ` → ${t.summary}`])) : null].filter(Boolean);
  return h("div", { class: "msg msg-assistant" }, h("div", { class: "bubble" },
    h("div", { class: "msg-head" }, h("strong", {}, "DealDesk"),
      h("span", { class: `pill pill-${modeTone}` }, modeLabel + (m.mode !== "scripted" && m.model ? ` · ${m.model}` : ""))),
    h("p", { class: "msg-text" }, m.text),
    (m.warnings || []).map((w) => h("div", { class: "warning" }, w)),
    m.cost_update ? costUpdateBlock(m.cost_update) : quoteCards(m.quote),
    forecastBlock(m.forecast),
    (m.actions || []).includes("apply_cost_update")
      ? h("button", { type: "button", class: "btn btn-warn inline-action", onclick: () => send(APPLY_MESSAGE) }, APPLY_MESSAGE)
      : null,
    list("From documents", (s.documents || []).map((d) => h("li", {}, d.text, d.citations.map((n) => citeButton(n, m, host))))),
    list("Missing or unconfirmed information", (s.missing || []).map((t) => h("li", {}, t))),
    host,
    details.length ? h("details", { class: "more" }, h("summary", {}, "How this was calculated"), details) : null));
}

function eventMessage(m) {
  if (m.kind === "tool_call") {
    const r = m.result;
    const args = Object.entries(m.arguments || {}).map(([k, v]) => `${k}=${JSON.stringify(v)}`).join(", ");
    return h("div", { class: "msg msg-event agent" }, h("div", { class: "bubble" },
      h("div", { class: "msg-head" }, h("strong", {}, "Local agent tool call"), h("span", { class: "pill pill-ok" }, m.caller)),
      h("p", { class: "msg-text" }, `${m.tool}(${args}) → ${m.summary}`),
      m.tool === "price_deal" ? [(r.messages || []).map((w) => h("div", { class: "warning" }, w)), quoteCards(r)] : null,
      m.tool === "apply_demo_cost_update" ? costUpdateBlock(r) : null,
      m.tool === "forecast_costs" ? forecastBlock(r) : null,
      m.tool === "search_documents" ? citationsBlock(r.map((c, i) => ({ ...c, n: i + 1 }))) : null));
  }
  const u = m.cost_update;
  return h("div", { class: "msg msg-event" }, h("div", { class: "bubble" },
    h("div", { class: "msg-head" }, h("strong", {}, "Cost update"), h("span", { class: "pill pill-warn" }, SOURCE_LABELS[u.source] || u.source)),
    h("p", { class: "msg-text" }, u.already_applied
      ? `Feed ${u.feed.feed_version} was already applied; no duplicate review was opened.`
      : (u.source === "scheduled_watcher"
        ? `The scheduled watcher found feed ${u.feed.feed_version} in the local incoming folder.`
        : `Feed ${u.feed.feed_version} was applied manually.`) +
        ` The open quote is unchanged; review #${u.event.id} is open with a separate revised appraisal.`),
    ((u.revised && u.revised.messages) || []).map((t) => h("div", { class: "warning" }, t)),
    costUpdateBlock(u)));
}

function renderMessage(m) {
  if (m.role === "user") return h("div", { class: "msg msg-user" }, h("div", { class: "bubble" }, m.text));
  if (m.role === "event") return eventMessage(m);
  return assistantMessage(m);
}

function render(extra = []) {
  if (state) renderStatus(state.status);
  const box = $("messages");
  const items = (state ? state.messages : []).map(renderMessage).concat(extra);
  box.replaceChildren(...(items.length ? items : [h("div", { class: "empty" },
    h("h2", {}, "Ask about the demo deal"),
    h("p", {}, "Lakeshore Distribution Cooperative is buying 100 CR-200 Edge Gateways with installation and 12 months of managed service (list $160,000.00). Try a suggested question below."))]));
  box.scrollTop = box.scrollHeight;
  setBusy(busy);
}

function setBusy(value) {
  busy = value;
  for (const el of [$("send-btn"), $("message-input"), $("reset-btn"), ...document.querySelectorAll(".chip, .inline-action")]) {
    el.disabled = value;
  }
}

const loadingBubble = () => h("div", { class: "msg msg-assistant" }, h("div", { class: "bubble" },
  h("span", { class: "loading" }, h("span", { class: "dot" }), h("span", { class: "dot" }), h("span", { class: "dot" }),
    state && state.status.mode === "local_model" ? " Calling local tools and the local model…" : " Calling local tools…")));
const errorBubble = (err) => h("div", { class: "msg msg-error" }, h("div", { class: "bubble" },
  `Request failed: ${err.message}. Nothing was changed; try again.`));

// ---------- actions ----------
async function send(text) {
  const message = text.trim();
  if (!message || busy) return;
  $("message-input").value = "";
  const mine = h("div", { class: "msg msg-user" }, h("div", { class: "bubble" }, message));
  busy = true;
  render([mine, loadingBubble()]);
  try {
    const result = await api("/api/chat", { method: "POST", body: JSON.stringify({ message }) });
    state = result.state;
    busy = false;
    render();
  } catch (err) {
    busy = false;
    render([mine, errorBubble(err)]);
  }
  $("message-input").focus();
}

async function resetDemo() {
  if (busy) return;
  busy = true;
  setBusy(true);
  try {
    state = await api("/api/reset", { method: "POST" });
    busy = false;
    render();
  } catch (err) {
    busy = false;
    render([errorBubble(err)]);
  }
  $("message-input").focus();
}

async function refresh() {
  try {
    const next = await api("/api/state");
    if (busy) return;
    const changed = !state || next.messages.length !== state.messages.length
      || JSON.stringify(next.status) !== JSON.stringify(state.status);
    state = next;
    if (changed) render();
  } catch (err) {
    $("mode-pill").className = "pill pill-bad";
    $("mode-pill").textContent = "Server unreachable";
  }
}

$("composer").addEventListener("submit", (event) => { event.preventDefault(); send($("message-input").value); });
$("suggestions").addEventListener("click", (event) => {
  const chip = event.target.closest(".chip");
  if (chip) send(chip.textContent);
});
$("reset-btn").addEventListener("click", resetDemo);

refresh();
setInterval(() => { if (!busy) refresh(); }, 4000);
