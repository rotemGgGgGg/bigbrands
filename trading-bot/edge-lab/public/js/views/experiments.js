// Experiment Lab: Draft → Running → Completed → Reviewed → Accepted / Rejected.
// A variation keeps a snapshot of its base strategy, so every change is visible as a diff.
import { api } from "../api.js";
import { $, $$, esc, fmt, signCls, skeleton, emptyState, toast, markdown } from "../util.js";
import { icon } from "../icons.js";
import { state } from "../state.js";

const STAGES = ["draft", "running", "completed", "reviewed", "decided"];
const FIELDS = [["entry", "Entry conditions"], ["exit", "Exit conditions"], ["filters", "Filters"], ["params", "Parameters"]];
let picked = new Set();

export default async function experiments(main, [id]) {
  if (id && id.startsWith("new")) { const base = new URLSearchParams(id.split("?")[1] || "").get("base"); await list(main); return newModal(base); }
  if (id) return detail(main, id);
  return list(main);
}

async function list(main) {
  main.innerHTML = skeleton([60, 320]);
  const xs = await api.experiments();
  state.context = "Experiment Lab: list of experiments.";
  main.innerHTML = `
  <div class="page wide">
    <div class="page-head fade-in"><div><h1>Experiments</h1><p>Change one thing at a time. The original strategy is never modified.</p></div>
      <div class="actions">${picked.size >= 2 ? `<button class="btn sm" id="cmp">${icon("compare", 14)} Compare ${picked.size}</button>` : ""}<button class="btn sm primary" id="new">${icon("plus", 14)} New experiment</button></div></div>
    ${xs.length ? `<div class="table-wrap fade-in d1"><table class="data"><thead><tr><th class="chk"></th><th class="l">Experiment</th><th class="l">Status</th><th class="l">Changed</th><th>Trades/yr</th><th>Win %</th><th>Avg R</th><th>2020–26</th><th>p random</th><th class="l">Updated</th></tr></thead><tbody>
      ${xs.map((x) => { const m = x.result?.metrics || {}; return `<tr class="clickable" data-id="${x.id}" tabindex="0"><td class="chk"><input type="checkbox" class="checkbox" data-id="${x.id}" ${picked.has(x.id) ? "checked" : ""} aria-label="Select ${esc(x.name)}"></td>
        <td class="name l">${esc(x.name)}<small>${esc(x.baseName ? `from ${x.baseName}` : "new strategy")}</small></td><td class="l"><span class="pill ${x.status}">${x.status}</span></td>
        <td class="l muted" style="font-family:var(--sans)">${esc(changed(x).map((f) => f[1].split(" ")[0]).join(", ") || "—")}</td>
        <td>${num(m.trades_per_year, 0)}</td><td>${num(m.win_rate, 1)}</td><td class="${signCls(m.avg_r)}">${fmt.r(m.avg_r, 3)}</td><td class="${signCls(m.oos_avg_r)}">${fmt.r(m.oos_avg_r, 3)}</td><td>${m.p_random ?? "—"}</td>
        <td class="l muted" style="font-family:var(--sans)">${fmt.ago(x.history.at(-1)?.at || x.createdAt)}</td></tr>`; }).join("")}</tbody></table></div><div id="compare"></div>`
      : `<div class="card fade-in d1">${emptyState(icon("flask"), "No experiments yet", "Start from a strategy, change its entry, exit or filters, and send it to the research agent. Results come back with the same gates as every other test.", `<button class="btn sm primary" id="new2">${icon("plus", 13)} New experiment</button>`)}</div>`}
  </div>`;
  $("#new", main).onclick = () => newModal();
  $("#new2", main) && ($("#new2", main).onclick = () => newModal());
  main.querySelector("tbody")?.addEventListener("click", (e) => {
    const cb = e.target.closest(".checkbox"); if (cb) { cb.checked ? picked.add(cb.dataset.id) : picked.delete(cb.dataset.id); list(main); return; }
    const tr = e.target.closest("tr[data-id]"); if (tr) location.hash = `#experiments/${tr.dataset.id}`;
  });
  $("#cmp", main) && ($("#cmp", main).onclick = () => compare(main, xs.filter((x) => picked.has(x.id))));
}

function compare(main, xs) {
  const rows = [["Trades / yr", "trades_per_year", 0], ["Win %", "win_rate", 1], ["Avg R", "avg_r", 3, true], ["2012–19 avg R", "is_avg_r", 3, true], ["2020–26 avg R", "oos_avg_r", 3, true], ["2020–26 t", "oos_t", 2], ["Positive years", "positive_years"], ["p random", "p_random"], ["Verdict", "verdict"]];
  $("#compare", main).innerHTML = `<div class="section-title">Comparison <span class="caption">metrics reported by each run</span></div><div class="table-wrap"><table class="data" style="min-width:600px"><thead><tr><th class="l">Metric</th>${xs.map((x) => `<th>${esc(x.name)}</th>`).join("")}</tr></thead><tbody>
    ${rows.map(([l, key, d, r]) => `<tr><td class="l" style="font-family:var(--sans)">${l}</td>${xs.map((x) => { const v = x.result?.metrics?.[key]; return `<td class="${r ? signCls(v) : ""}">${v == null ? "—" : typeof v === "number" ? (r ? fmt.r(v, d) : fmt.n(v, d)) : esc(v)}</td>`; }).join("")}</tr>`).join("")}
    <tr><td class="l" style="font-family:var(--sans)">Changed</td>${xs.map((x) => `<td style="font-family:var(--sans)">${esc(changed(x).map((f) => f[1]).join(", ") || "—")}</td>`).join("")}</tr></tbody></table></div>`;
}

async function newModal(baseId) {
  const all = await api.strategies();
  const back = document.createElement("div"); back.className = "modal-back";
  back.innerHTML = `<form class="modal" role="dialog" aria-modal="true" aria-labelledby="nm-t"><div class="modal-head"><h2 id="nm-t">New experiment</h2><p class="caption" style="margin:4px 0 0">Starts as a draft. The base strategy's rules are copied so you can change them.</p></div>
    <div class="modal-body">
      <label class="field"><span>Base strategy</span><select class="select" id="nm-base"><option value="">None — a new strategy</option>${all.map((s) => `<option value="${s.id}" ${s.id === baseId ? "selected" : ""}>${esc(s.name)} · ${s.status.toLowerCase()}</option>`).join("")}</select></label>
      <label class="field"><span>Name</span><input class="input" id="nm-name" placeholder="e.g. RDM 1:10 + volatility filter" required></label>
      <label class="field"><span>Hypothesis</span><textarea class="input" id="nm-h" placeholder="What should change, and why it would work."></textarea></label>
    </div><div class="modal-foot"><button type="button" class="btn ghost" id="nm-cancel">Cancel</button><button class="btn primary" type="submit">Create draft</button></div></form>`;
  document.body.append(back);
  const close = () => { back.remove(); if (location.hash.startsWith("#experiments/new")) history.replaceState(null, "", "#experiments"); };
  const sel = $("#nm-base", back), nm = $("#nm-name", back);
  const suggest = () => { const s = all.find((x) => x.id === sel.value); if (!nm.dataset.touched) nm.value = s ? `${s.name} · variation` : ""; };
  sel.onchange = suggest; nm.oninput = () => (nm.dataset.touched = 1); suggest();
  $("#nm-cancel", back).onclick = close; back.addEventListener("click", (e) => { if (e.target === back) close(); });
  back.addEventListener("keydown", (e) => { if (e.key === "Escape") close(); });
  setTimeout(() => nm.focus(), 30);
  back.querySelector("form").addEventListener("submit", async (e) => {
    e.preventDefault();
    try { const x = await api.createExperiment({ baseId: sel.value || null, name: nm.value.trim(), hypothesis: $("#nm-h", back).value }); back.remove(); location.hash = `#experiments/${x.id}`; }
    catch (err) { toast(err.message, "err"); }
  });
}

async function detail(main, id) {
  main.innerHTML = skeleton([40, 80, 360]);
  let x;
  try { x = (await api.experiments()).find((e) => e.id === id); } catch (e) { main.innerHTML = `<div class="page">${esc(e.message)}</div>`; return; }
  if (!x) { main.innerHTML = `<div class="page">${emptyState(icon("flask"), "Experiment not found", "It may have been deleted.", `<a class="btn sm" href="#experiments">Back to experiments</a>`)}</div>`; return; }
  state.context = `Experiment "${x.name}" (${x.status}), base: ${x.baseName || "none"}. Entry: ${x.entry}. Exit: ${x.exit}. Filters: ${x.filters}.`;
  const draft = x.status === "draft", m = x.result?.metrics;
  main.innerHTML = `
  <div class="page">
    <a class="crumb fade-in" href="#experiments">${icon("arrowLeft", 13)} Experiments</a>
    <div class="page-head fade-in"><div><div class="row" style="gap:10px"><h1>${esc(x.name)}</h1><span class="pill ${x.status}">${x.status}</span></div><p>${esc(x.baseName ? `Variation of ${x.baseName}` : "New strategy")} · created ${fmt.date(x.createdAt)}</p></div>
      <div class="actions">
        <button class="btn sm ghost" id="dup">${icon("copy", 14)} Duplicate</button>
        ${draft ? `<button class="btn sm ghost danger" id="del">${icon("trash", 14)} Delete</button><button class="btn sm" id="save">Save draft</button><button class="btn sm accent" id="run">${icon("play", 13)} Run with agent</button>` : ""}
        ${x.status === "running" && x.conversationId ? `<a class="btn sm" href="#research/${x.conversationId}">${icon("cpu", 14)} Watch the run</a>` : ""}
        ${x.status === "completed" ? `<button class="btn sm primary" data-to="reviewed">Mark reviewed</button>` : ""}
        ${x.status === "reviewed" ? `<button class="btn sm ghost danger" data-to="rejected">Reject</button><button class="btn sm primary" data-to="accepted">Accept</button>` : ""}
        ${["completed", "reviewed", "rejected"].includes(x.status) ? `<button class="btn sm ghost" data-to="draft">Back to draft</button>` : ""}
      </div></div>
    <div class="card fade-in d1" style="margin-bottom:16px"><div class="card-body">${stepper(x)}</div></div>
    ${x.hypothesis || draft ? `<div class="card fade-in d1" style="margin-bottom:16px"><div class="card-head"><span class="card-title">Hypothesis</span></div><div class="card-body">${draft ? `<textarea class="input" id="f-hypothesis" aria-label="Hypothesis">${esc(x.hypothesis)}</textarea>` : `<p class="rule-block">${esc(x.hypothesis)}</p>`}</div></div>` : ""}
    <div class="card fade-in d2"><div class="card-head"><span class="card-title">Rules</span><span class="card-sub">${x.baseName ? "base on the left, this variation on the right" : ""}</span></div><div class="card-body">
      ${draft ? `<div class="grid" style="gap:14px">${FIELDS.map(([f, l]) => `<label class="field"><span>${l}${x.baseName && (x[f] || "") !== (x.base[f] || "") ? ' <span class="pill running" style="height:17px">changed</span>' : ""}</span><textarea class="input" id="f-${f}" rows="3">${esc(x[f])}</textarea>${x.baseName ? `<small>Base: ${esc(x.base[f] || "—")}</small>` : ""}</label>`).join("")}</div>`
        : `<div class="diff"><div class="h">Field</div><div class="h">Base</div><div class="h">This experiment</div>${FIELDS.map(([f, l]) => { const ch = (x[f] || "") !== (x.base[f] || ""); return `<div class="k">${l}</div><div class="${ch ? "changed" : ""}">${esc(x.base[f] || "—")}</div><div class="${ch ? "changed new" : ""}">${esc(x[f] || "—")}</div>`; }).join("")}</div>`}
    </div></div>
    ${x.result ? `<div class="section-title">Result <span class="caption">${fmt.date(x.result.at)} ${fmt.time(x.result.at)}${x.result.conversationId ? ` · <a href="#research/${x.result.conversationId}">open conversation</a>` : ""}</span></div>
      ${m ? `<div class="kpis" style="--n:6">${k("Trades / yr", num(m.trades_per_year, 0))}${k("Win rate", m.win_rate == null ? "—" : `${num(m.win_rate, 1)}%`)}${k("Avg R", fmt.r(m.avg_r, 3), "", signCls(m.avg_r))}${k("2020–26", fmt.r(m.oos_avg_r, 3), `t ${m.oos_t ?? "—"}`, signCls(m.oos_avg_r))}${k("Positive years", esc(m.positive_years ?? "—"))}${k("p random", esc(m.p_random ?? "—"), esc(m.verdict ?? ""))}</div>` : `<div class="caption">The run did not return the metrics block, so there is nothing to compare. The full answer is below.</div>`}
      ${x.result.error ? `<div class="err-box" style="margin-top:12px"><b>Run ended with an error.</b> ${esc(x.result.error)}</div>` : ""}
      <div class="card" style="margin-top:12px"><div class="card-body"><div class="md">${markdown(x.result.text || "")}</div></div></div>` : ""}
    <div class="section-title">Notes</div>
    <div class="card"><div class="card-body"><textarea class="input" id="f-notes" aria-label="Notes" placeholder="Decisions, doubts, what to try next.">${esc(x.notes)}</textarea><div class="row" style="margin-top:8px"><button class="btn sm" id="save-notes">Save notes</button></div></div></div>
    <div class="section-title">Timeline</div>
    <div class="list">${x.history.slice().reverse().map((h) => `<div class="list-item"><span class="pill ${h.status}">${h.status}</span><div class="li-main"><div class="li-title">${esc(h.note || "")}</div></div><div class="li-right muted">${fmt.date(h.at)} ${fmt.time(h.at)}</div></div>`).join("")}</div>
  </div>`;
  const vals = () => Object.fromEntries([["hypothesis"], ...FIELDS].map(([f]) => [f, $(`#f-${f}`, main)?.value ?? x[f]]));
  const reload = () => detail(main, id);
  $("#dup", main).onclick = async () => { const d = await api.duplicateExperiment(id); location.hash = `#experiments/${d.id}`; };
  $("#save", main) && ($("#save", main).onclick = async () => { await api.updateExperiment(id, vals()); toast("Draft saved"); reload(); });
  $("#del", main) && ($("#del", main).onclick = async (e) => { if (e.currentTarget.dataset.armed) { await api.deleteExperiment(id); location.hash = "#experiments"; } else { e.currentTarget.dataset.armed = 1; e.currentTarget.innerHTML = `${icon("trash", 14)} Click again to delete`; } });
  $("#run", main) && ($("#run", main).onclick = async (e) => {
    e.currentTarget.disabled = true;
    try { await api.updateExperiment(id, vals()); const r = await api.runExperiment(id); toast("Sent to the research agent"); location.hash = `#research/${r.conversationId}`; }
    catch (err) { toast(err.message, "err"); e.currentTarget.disabled = false; }
  });
  $$("[data-to]", main).forEach((b) => b.addEventListener("click", async () => { try { await api.updateExperiment(id, { status: b.dataset.to }); reload(); } catch (err) { toast(err.message, "err"); } }));
  $("#save-notes", main).onclick = async () => { await api.updateExperiment(id, { notes: $("#f-notes", main).value }); toast("Notes saved"); };
}

function stepper(x) {
  const idx = { draft: 0, running: 1, completed: 2, reviewed: 3, accepted: 4, rejected: 4 }[x.status];
  const labels = ["Draft", "Running", "Completed", "Reviewed", x.status === "rejected" ? "Rejected" : x.status === "accepted" ? "Accepted" : "Accepted / Rejected"];
  return `<div class="stepper">${labels.map((l, i) => `${i ? '<span class="ln"></span>' : ""}<span class="st ${i < idx ? "done" : i === idx ? "now" : ""} ${i === 4 && x.status === "rejected" ? "bad" : ""}"><i>${i < idx ? "✓" : i + 1}</i>${l}</span>`).join("")}</div>`;
}

const changed = (x) => (x.baseName ? FIELDS.filter(([f]) => (x[f] || "") !== (x.base?.[f] || "")) : []);
const num = (v, d) => (v == null ? "—" : typeof v === "number" ? fmt.n(v, d) : esc(v));
const k = (l, v, s = "", cls = "") => `<div class="kpi"><div class="kpi-label">${esc(l)}</div><div class="kpi-value ${cls}">${v}</div><div class="kpi-sub">${s}</div></div>`;
