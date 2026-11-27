// Static build API: the same interface as api.js, computed in the browser from data/data.json and data/trades.json.
// Used when the app is hosted without the Node server (Lovable, Netlify, GitHub Pages). No research agent:
// it needs Claude Code on your own computer, so chat and experiment runs explain that instead of failing silently.
import { enrich, summary } from "./engine/enrich.mjs";
import { simulate } from "./engine/montecarlo.mjs";
import { portfolio as runPortfolio } from "./engine/portfolio.mjs";

const AGENT_MSG = "The research agent runs on your computer. Start Edge Lab there and connect it in Settings → Connect your computer. Everything else works here.";
let cache = null;

async function load() {
  if (cache) return cache;
  const [reg, trades, commits] = await Promise.all([
    fetch("data/data.json").then((r) => r.json()),
    fetch("data/trades.json").then((r) => r.json()).catch(() => ({})),
    fetch("data/history.json").then((r) => r.json()).catch(() => []),
  ]);
  const strategies = reg.strategies.map((s) => enrich(s, trades[s.id] || (s.series && trades[s.series])));
  cache = { reg, trades, strategies, commits };
  return cache;
}
const dataApi = (c) => ({
  load: () => ({ strategies: c.strategies, trades: c.trades }),
  series(id) { const s = c.strategies.find((x) => x.id === id); const tr = s && (c.trades[id] || (s.series && c.trades[s.series])); return tr ? { t: tr.t, r: tr.r, units: tr.units } : null; },
});

// ------------------------------------------------------------ browser storage (per device)
const mem = {};
const ls = {
  get(k, d) { try { const v = localStorage.getItem(k); return v == null ? (mem[k] ?? d) : JSON.parse(v); } catch { return mem[k] ?? d; } },
  set(k, v) { mem[k] = v; try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* blocked */ } return v; },
};
const uid = (p) => `${p}_${Math.random().toString(16).slice(2, 12)}`;
const now = () => new Date().toISOString();
const log = (type, title, extra = {}) => { const ev = { id: uid("ev"), at: now(), type, title, ...extra }; ls.set("edge.events", [ev, ...ls.get("edge.events", [])].slice(0, 500)); };
const fail = (msg) => { throw new Error(msg); };

const FIELDS = ["name", "hypothesis", "entry", "exit", "filters", "params", "notes"];
const NEXT = { draft: ["running"], running: ["completed", "draft"], completed: ["reviewed", "draft"], reviewed: ["accepted", "rejected", "draft"], accepted: [], rejected: ["draft"] };

export const api = {
  session: async () => ({ authRequired: false, authenticated: true }),
  login: async () => ({ ok: true }), logout: async () => ({ ok: true }), logoutAll: async () => ({ ok: true }),
  async health() {
    const c = await load();
    return {
      static: true, agent: { available: false, error: AGENT_MSG }, workspace: "static build", runningJobs: 0,
      settings: { permission: "read", model: "", userName: "Rotem", billing: "subscription", maxBudgetUsd: 2 },
      permissions: { read: { label: "Not available in the static build", description: AGENT_MSG, tools: [] } }, models: [{ id: "", label: "—" }],
      files: [{ key: "registry", path: "data/data.json", exists: true, modified: c.reg.updated?.replace(" UTC", "Z").replace(" ", "T") || null }],
      security: { passwordProtected: false, host: "static hosting", allowedHosts: [], sessions: 0 }, billing: { apiKeyConfigured: false },
    };
  },
  detect: async () => ({ available: false, error: AGENT_MSG }),
  async overview() {
    const c = await load(), S = c.strategies, live = S.filter((s) => s.status === "LIVE");
    const best = [...live].filter((s) => s.oosT != null).sort((a, b) => b.oosT - a.oosT)[0];
    const exps = ls.get("edge.experiments", []);
    const activity = [...ls.get("edge.events", []).slice(0, 8), ...c.commits.slice(0, 8)].sort((a, b) => b.at.localeCompare(a.at)).slice(0, 8);
    return {
      updated: c.reg.updated, theoriesTested: c.reg.theories_tested, book: c.reg.book,
      counts: { total: S.length, live: live.length, watch: S.filter((s) => s.status === "WATCH").length, dead: S.filter((s) => s.status === "DEAD").length, experiments: exps.length },
      best: best ? summary(best) : null, liveExpectancy: live.length ? live.reduce((a, s) => a + (s.expectancy ?? 0), 0) / live.length : null,
      live: live.map(summary), recentExperiments: exps.slice(0, 5), activity,
    };
  },
  strategies: async () => (await load()).strategies.map(summary),
  async strategy(id) { const s = (await load()).strategies.find((x) => x.id === id); return s || fail("Strategy not found"); },
  sp: async () => (await load()).reg.sp || {},
  async montecarlo(b) {
    const c = await load(), d = dataApi(c);
    if (b.weights) return { ...runPortfolio(d, b.weights, {}).montecarlo, label: "Portfolio" };
    const s = d.series(b.strategy); if (!s) fail("No trade series for that strategy");
    const st = c.strategies.find((x) => x.id === b.strategy);
    return { ...simulate(s.r, { ...b, horizon: b.horizon || Math.round(st.perYear) }), label: b.strategy, units: s.units };
  },
  async portfolio(b) { return runPortfolio(dataApi(await load()), b.weights || {}, b); },

  conversations: async () => [], conversation: async () => fail("Conversations live in the local Edge Lab app."), deleteConversation: async () => ({ ok: true }), updateConversation: async () => fail("Conversations live in the local Edge Lab app."), usage: async () => ({ limits: null, today: { runs: 0, costUsd: 0 } }),
  chat: async () => fail(AGENT_MSG), cancel: async () => ({ ok: true }),

  experiments: async () => ls.get("edge.experiments", []),
  async createExperiment(b) {
    const S = (await load()).strategies, base = b.baseId ? S.find((s) => s.id === b.baseId) : null;
    const snap = base ? { entry: base.entry || base.rule || "", exit: base.exit || "", filters: "", params: base.params ? JSON.stringify(base.params) : "" } : { entry: "", exit: "", filters: "", params: "" };
    const x = { id: uid("exp"), createdAt: now(), status: "draft", baseId: base?.id || null, baseName: base?.name || null, base: snap,
      name: String(b.name || (base ? `${base.name} variation` : "Untitled experiment")).slice(0, 120), hypothesis: String(b.hypothesis || ""),
      entry: snap.entry, exit: snap.exit, filters: "", params: snap.params, notes: "", history: [{ at: now(), status: "draft", note: base ? `Created from ${base.name}` : "Created" }], result: null };
    ls.set("edge.experiments", [x, ...ls.get("edge.experiments", [])]); log("experiment", `Experiment created: ${x.name}`, { experimentId: x.id });
    return x;
  },
  async updateExperiment(id, b) {
    const all = ls.get("edge.experiments", []), x = all.find((e) => e.id === id); if (!x) fail("Experiment not found");
    if (b.status && b.status !== x.status) {
      if (!NEXT[x.status].includes(b.status) || b.status === "running") fail(`Cannot move from ${x.status} to ${b.status}`);
      x.status = b.status; x.history.push({ at: now(), status: b.status, note: String(b.note || "") }); log("experiment", `Experiment ${b.status}: ${x.name}`, { experimentId: x.id });
    }
    if (x.status === "draft") { for (const f of FIELDS) if (f in b) x[f] = String(b[f]); } else if ("notes" in b) x.notes = String(b.notes);
    ls.set("edge.experiments", all); return x;
  },
  async duplicateExperiment(id) {
    const all = ls.get("edge.experiments", []), src = all.find((e) => e.id === id); if (!src) fail("Experiment not found");
    const x = { ...structuredClone(src), id: uid("exp"), name: `${src.name} (copy)`, createdAt: now(), status: "draft", result: null, history: [{ at: now(), status: "draft", note: `Duplicated from ${src.name}` }] };
    ls.set("edge.experiments", [x, ...all]); return x;
  },
  async deleteExperiment(id) { ls.set("edge.experiments", ls.get("edge.experiments", []).filter((e) => e.id !== id)); return { ok: true }; },
  runExperiment: async () => fail(AGENT_MSG),

  async history() { const c = await load(); return [...ls.get("edge.events", []), ...c.commits].sort((a, b) => b.at.localeCompare(a.at)); },
  settings: async () => (await api.health()).settings,
  saveSettings: async () => fail("Settings control the research agent, which runs only in the local Edge Lab app."),
  rebuild: async () => fail("The static build serves a snapshot of the research data. Rebuild it from the repository (npm run build:static)."),
};

export function stream() { return Promise.resolve(); }
