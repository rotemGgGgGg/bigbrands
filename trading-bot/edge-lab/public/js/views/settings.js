// Settings: agent connection, permission level, model, data sources.
import { api } from "../api.js";
import { $, $$, esc, fmt, skeleton, toast } from "../util.js";
import { icon } from "../icons.js";
import { state } from "../state.js";

export default async function settings(main, _p, { refreshHealth }) {
  main.innerHTML = skeleton([60, 200, 300]);
  await refreshHealth();
  const h = state.health, a = h.agent;
  main.innerHTML = `
  <div class="page" style="max-width:860px">
    <div class="page-head fade-in"><div><h1>Settings</h1><p>How the research agent connects and what it may do.</p></div></div>

    <div class="card fade-in d1"><div class="card-head"><span class="card-title">Agent connection</span><div class="right"><button class="btn sm" id="recheck">${icon("refresh", 13)} Re-check</button></div></div>
      <div class="card-body"><div class="row" style="gap:12px;margin-bottom:14px"><span class="status-dot ${a.available ? "ok" : "off"}" style="margin:0"></span>
        <div><div>${a.available ? `Claude Code ${esc(a.version)}` : "Not connected"}</div><div class="caption">${a.available ? "The local server runs the Claude Code CLI in headless mode inside your research folder." : esc(a.error || "")}</div></div></div>
        <dl class="kv"><dt>Workspace</dt><dd>${esc(h.workspace)}</dd><dt>Bridge</dt><dd>claude -p --output-format stream-json</dd><dt>Approval mode</dt><dd>dontAsk + explicit allow-list</dd><dt>Runs in progress</dt><dd>${h.runningJobs}</dd></dl>
        ${a.available ? "" : `<div class="err-box" style="margin-top:14px"><b>To connect:</b> install Claude Code, run <code>claude</code> once in a terminal to sign in, then press Re-check. If the binary lives elsewhere, start the server with <code>CLAUDE_BIN=/path/to/claude npm start</code>.</div>`}
      </div></div>

    <div class="section-title fade-in d2">Permission level <span class="caption">applies to every new agent run</span></div>
    <div class="perm fade-in d2" role="radiogroup" aria-label="Permission level">${Object.entries(h.permissions).map(([key, p]) => `<label><input type="radio" name="perm" value="${key}" ${h.settings.permission === key ? "checked" : ""}><div><b>${esc(p.label)}</b><p>${esc(p.description)}</p><div class="params">${p.tools.map((t) => `<span class="param">${esc(t)}</span>`).join("")}</div></div></label>`).join("")}</div>
    <p class="caption" style="margin-top:10px">Anything outside the selected list is refused automatically; the agent never asks the browser for approval. Web access is not on any list.</p>

    <div class="section-title fade-in d3">Model</div>
    <div class="card fade-in d3"><div class="card-body"><label class="field"><span>Model used by the agent</span><select class="select" id="model" style="max-width:320px">${h.models.map((m) => `<option value="${m.id}" ${m.id === h.settings.model ? "selected" : ""}>${esc(m.label)}</option>`).join("")}</select><small>"Claude Code default" uses whatever your Claude Code is set to. Usage counts against your own Claude plan.</small></label></div></div>

    <div class="section-title fade-in d3">Billing <span class="caption">who pays for agent runs</span></div>
    <div class="perm fade-in d3" role="radiogroup" aria-label="Billing">
      <label><input type="radio" name="billing" value="subscription" ${h.settings.billing !== "api" ? "checked" : ""}><div><b>Claude subscription</b><p>Uses the account Claude Code is signed in with (run <code>claude</code>, then <code>/login</code>, and pick your Claude account). Runs count against your plan's limits. Any API key in the environment is ignored.</p></div></label>
      <label><input type="radio" name="billing" value="api" ${h.settings.billing === "api" ? "checked" : ""} ${h.billing.apiKeyConfigured ? "" : "disabled"}><div><b>Claude API key</b><p>Pay per token with your Anthropic API key. The key stays on the server (environment variable <code>EDGE_LAB_API_KEY</code>) and never reaches the browser. ${h.billing.apiKeyConfigured ? "Key detected." : '<span class="neg">No key set on the server.</span>'}</p>
        <div class="field" style="max-width:220px"><span>Spend cap per run (USD)</span><input class="input mono" id="budget" type="number" min="0.1" max="50" step="0.1" value="${h.settings.maxBudgetUsd}" aria-label="Spend cap per run in US dollars"></div></div></label>
    </div>

    <div class="section-title fade-in d3">Access</div>
    <div class="card fade-in d3"><div class="card-body"><dl class="kv">
      <dt>Who can open it</dt><dd>${h.security.passwordProtected ? "anyone with the password" : "this computer only (no login)"}</dd>
      <dt>Listening on</dt><dd>${esc(h.security.host)}</dd>
      <dt>Extra allowed hosts</dt><dd>${esc(h.security.allowedHosts.join(", ") || "none")}</dd>
      ${h.security.passwordProtected ? `<dt>Signed-in devices</dt><dd>${h.security.sessions}</dd>` : ""}</dl>
      ${h.security.passwordProtected ? `<div class="row" style="margin-top:12px"><button class="btn sm" id="logout">Sign out</button><button class="btn sm ghost danger" id="logout-all">Sign out every device</button></div>`
        : `<p class="caption" style="margin:12px 0 0">To open it from your phone, see "Access from your phone" in the README: Tailscale plus a password, never a public address.</p>`}
    </div></div>

    <div class="section-title fade-in d4">Research data</div>
    <div class="card fade-in d4"><div class="card-body"><div class="list">${h.files.map((f) => `<div class="list-item"><span class="li-icon">${icon("database", 13)}</span><div class="li-main"><div class="li-title mono" style="font-size:12px">${esc(f.path)}</div><div class="li-sub">${f.exists ? `modified ${fmt.date(f.modified)} ${fmt.time(f.modified)}` : "missing"}</div></div></div>`).join("")}</div>
      <div class="row" style="margin-top:12px"><button class="btn sm" id="rebuild">${icon("refresh", 13)} Rebuild registry</button><span class="caption">Runs <code>python3 build.py</code> in research/lab. Trade series come from <code>export_trades.py</code>.</span></div></div></div>
  </div>`;
  $("#recheck", main).onclick = async () => { await api.detect(); await refreshHealth(); toast("Agent status refreshed"); settings(main, _p, { refreshHealth }); };
  $$("input[name=perm]", main).forEach((r) => r.addEventListener("change", async () => { await api.saveSettings({ permission: r.value }); await refreshHealth(); toast(`Permission level: ${h.permissions[r.value].label}`); }));
  $("#model", main).addEventListener("change", async (e) => { await api.saveSettings({ model: e.target.value }); await refreshHealth(); toast("Model updated"); });
  $$("input[name=billing]", main).forEach((r) => r.addEventListener("change", async () => { try { await api.saveSettings({ billing: r.value }); await refreshHealth(); toast(r.value === "api" ? "Billing: API key" : "Billing: Claude subscription"); } catch (e) { toast(e.message, "err"); settings(main, _p, { refreshHealth }); } }));
  $("#budget", main)?.addEventListener("change", async (e) => { try { await api.saveSettings({ maxBudgetUsd: +e.target.value }); toast(`Spend cap: $${(+e.target.value).toFixed(2)} per run`); } catch (err) { toast(err.message, "err"); } });
  $("#logout", main) && ($("#logout", main).onclick = async () => { await api.logout(); location.reload(); });
  $("#logout-all", main) && ($("#logout-all", main).onclick = async () => { await api.logoutAll(); location.reload(); });
  $("#rebuild", main).onclick = async (e) => { e.currentTarget.disabled = true; try { const r = await api.rebuild(); toast(`Registry rebuilt (${r.output})`); } catch (err) { toast(err.message, "err"); } finally { e.currentTarget.disabled = false; } };
}
