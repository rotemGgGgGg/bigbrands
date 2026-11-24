// Edge Lab shell: sidebar, router, floating agent dock and the side panel conversation.
import { api } from "./api.js";
import { $, $$, esc, toast } from "./util.js";
import { icon, logo } from "./icons.js";
import { state } from "./state.js";
import { chatbar, Thread, agentDot, agentLabel } from "./chat.js";
import welcome from "./views/welcome.js";
import research from "./views/research.js";
import overview from "./views/overview.js";
import strategies from "./views/strategies.js";
import montecarlo from "./views/montecarlo.js";
import portfolio from "./views/portfolio.js";
import experiments from "./views/experiments.js";
import history from "./views/history.js";
import graveyard from "./views/graveyard.js";
import settings from "./views/settings.js";

const VIEWS = { welcome, research, overview, strategies, montecarlo, portfolio, experiments, history, graveyard, settings };
const NAV = [
  ["overview", "Overview", "overview"], ["strategies", "Strategies", "strategies"], ["experiments", "Experiments", "flask"],
  ["portfolio", "Portfolio Lab", "layers"], ["montecarlo", "Monte Carlo", "dice"], ["history", "Research History", "history"], ["graveyard", "Graveyard", "grave"],
];
const store = { get(k, d) { try { const v = localStorage.getItem(k); return v == null ? d : JSON.parse(v); } catch { return d; } }, set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* private mode */ } } };

let cleanup = null, panelThread = null, dock = null;

function shell() {
  const collapsed = store.get("edge.sidebar.collapsed", false);
  $("#app").innerHTML = `
    <div class="app ${collapsed ? "collapsed" : ""}">
      <aside class="sidebar" aria-label="Main navigation">
        <div class="brand"><span class="brand-mark">${logo(14)}</span><span class="brand-name">Edge Lab</span>
          <button class="icon-btn" id="collapse" title="Collapse sidebar ([)" aria-label="Collapse sidebar">${icon("sidebar", 16)}</button></div>
        <nav class="nav">
          <a class="nav-item new" href="#research/new">${icon("plus", 15)}<span class="nav-label">New Research</span><span class="kbd nav-label">⌘K</span></a>
          ${NAV.map(([r, label, ic]) => `<a class="nav-item" data-route="${r}" href="#${r}">${icon(ic, 16)}<span class="nav-label">${label}</span></a>`).join("")}
          <div class="nav-section">Conversations</div>
          <div id="nav-convs"></div>
        </nav>
        <div class="side-foot">
          <a class="foot-row" href="#settings" id="agent-row" title="Agent connection">
            <span class="status-dot" id="agent-dot"></span><span class="txt"><span id="agent-title">Agent</span><small id="agent-sub">Connecting…</small></span></a>
          <a class="foot-row" href="#settings" title="Settings">${icon("settings", 15)}<span class="txt"><span>Settings</span><small id="env-sub">Research workspace</small></span></a>
          <div class="foot-row"><span class="avatar">R</span><span class="txt"><span>Rotem</span><small>Personal workspace</small></span></div>
        </div>
      </aside>
      <main class="main" id="main" tabindex="-1"></main>
    </div>
    <button class="icon-btn mobile-menu" id="mobile-menu" aria-label="Open navigation">${icon("menu", 18)}</button>
    <div class="dock" id="dock"></div>
    <aside class="panel" id="panel" aria-label="Research agent">
      <div class="panel-head"><span class="agent-mark" style="width:22px;height:22px">${logo(11)}</span><b id="panel-title">Research agent</b>
        <div class="right">
          <button class="icon-btn" id="panel-new" title="New conversation" aria-label="New conversation">${icon("plus", 15)}</button>
          <button class="icon-btn" id="panel-full" title="Open full conversation" aria-label="Open full conversation">${icon("expand", 15)}</button>
          <button class="icon-btn" id="panel-close" title="Close (Esc)" aria-label="Close panel">${icon("x", 15)}</button>
        </div></div>
      <div id="panel-body" style="flex:1;min-height:0"></div>
    </aside>`;
  document.body.classList.toggle("sb-collapsed", collapsed);
  $("#collapse").onclick = toggleSidebar;
  $("#mobile-menu").onclick = () => document.body.classList.toggle("sb-open");
  $(".sidebar").addEventListener("click", (e) => { if (e.target.closest("a")) document.body.classList.remove("sb-open"); });

  dock = chatbar({ compact: true, placeholder: "Ask the research agent…  ⌘K", onSubmit: (t, a) => openPanel({ text: t, attachment: a }) });
  $("#dock").append(dock.el);

  panelThread = new Thread($("#panel-body"), { compact: true, onConversation: (c) => { store.set("edge.panel.conv", c.id); $("#panel-title").textContent = c.title; loadConvNav(); } });
  $("#panel-close").onclick = closePanel;
  $("#panel-new").onclick = () => { store.set("edge.panel.conv", null); $("#panel-title").textContent = "Research agent"; panelThread.load(null); panelThread.bar.focus(); };
  $("#panel-full").onclick = () => { const id = panelThread.conv?.id; closePanel(); location.hash = id ? `#research/${id}` : "#research/new"; };
}

function toggleSidebar() {
  const app = $(".app"); app.classList.toggle("collapsed");
  const c = app.classList.contains("collapsed"); document.body.classList.toggle("sb-collapsed", c); store.set("edge.sidebar.collapsed", c);
}

export async function openPanel({ text, attachment, conversationId } = {}) {
  document.body.classList.add("panel-open");
  const id = conversationId ?? store.get("edge.panel.conv", null);
  if (!panelThread.conv || panelThread.conv.id !== id) { await panelThread.load(id); $("#panel-title").textContent = panelThread.conv?.title || "Research agent"; }
  if (text) { dock.clear(); await panelThread.send(text, attachment); }
  else panelThread.bar.focus();
}
function closePanel() { document.body.classList.remove("panel-open"); }

async function loadConvNav() {
  try {
    const convs = await api.conversations();
    const cur = location.hash.startsWith("#research/") ? location.hash.split("/")[1] : null;
    $("#nav-convs").innerHTML = convs.slice(0, 8).map((c) => `<a class="nav-item ${c.id === cur ? "active" : ""}" href="#research/${c.id}" title="${esc(c.title)}">${icon(state.busyConvs.has(c.id) ? "cpu" : "chat", 15)}<span class="nav-label" style="overflow:hidden;text-overflow:ellipsis">${esc(c.title)}</span></a>`).join("")
      || `<div class="caption nav-label" style="padding:4px 10px">No conversations yet</div>`;
  } catch { /* server restarting */ }
}

function paintAgent() {
  const h = state.health, dot = $("#agent-dot"); if (!dot) return;
  dot.className = `status-dot ${agentDot()}`;
  $("#agent-title").textContent = !h ? "Agent" : h.agent.available ? (state.busy ? "Agent working" : "Agent connected") : "Agent offline";
  $("#agent-sub").textContent = !h ? "Connecting…" : h.agent.available ? h.agent.version.replace(/\s*\(.*\)/, "") : "Open Settings";
  if (h) $("#env-sub").textContent = `${h.workspace.split("/").slice(-2).join("/")} · ${h.permissions[h.settings.permission]?.label}`;
}

export async function refreshHealth() {
  try { state.setHealth(await api.health()); } catch (e) { state.setHealth({ agent: { available: false, error: e.message }, settings: {}, permissions: {}, models: [], workspace: "" }); }
}

async function route() {
  const [name = "welcome", ...rest] = location.hash.replace(/^#/, "").split("/").filter(Boolean);
  const view = VIEWS[name] ? name : "welcome";
  cleanup?.(); cleanup = null; state.context = "";
  document.body.classList.toggle("welcome", view === "welcome");
  document.body.classList.toggle("route-research", view === "research");
  $$(".nav-item[data-route]").forEach((a) => a.classList.toggle("active", a.dataset.route === view));
  const main = $("#main"); main.scrollTop = 0;
  try { cleanup = (await VIEWS[view](main, rest.map(decodeURIComponent), { openPanel, refreshHealth, loadConvNav })) || null; }
  catch (e) { console.error(e); main.innerHTML = `<div class="page"><div class="err-box"><b>This page could not load</b><div>${esc(e.message)}</div></div></div>`; }
  loadConvNav();
}

document.addEventListener("keydown", (e) => {
  const mod = e.metaKey || e.ctrlKey;
  if (mod && e.key.toLowerCase() === "k") {
    e.preventDefault();
    if (document.body.classList.contains("welcome") || document.body.classList.contains("route-research")) { $("#main textarea")?.focus(); return; }
    if (document.body.classList.contains("panel-open")) panelThread.bar.focus(); else dock.focus();
  }
  if (e.key === "Escape" && document.body.classList.contains("panel-open")) closePanel();
  if (e.key === "[" && !e.target.closest("input, textarea, select") && !document.body.classList.contains("welcome")) toggleSidebar();
});

state.on(paintAgent);
state.on(() => loadConvNav());
shell();
window.addEventListener("hashchange", route);
refreshHealth().then(() => setInterval(refreshHealth, 30000));
route().then(() => document.body.classList.remove("booting"));
