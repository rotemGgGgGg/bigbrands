// Client for the Edge Lab server.
// Three modes:
//  · local app (served by the Node server): same-origin calls, cookie auth.
//  · static build + bridge: the page is hosted elsewhere (e.g. Lovable) and talks to the Edge Lab server on your
//    computer at the saved address, with the pairing code. The agent runs there, on your Claude Code sign-in.
//  · static build alone: everything computed in the browser from the data files; no agent.
const STATIC = document.documentElement.dataset.static === "1";
const BRIDGE_KEY = "edge.bridge";

export const bridge = {
  get() { try { return JSON.parse(localStorage.getItem(BRIDGE_KEY) || "null"); } catch { return null; } },
  set(v) { try { v ? localStorage.setItem(BRIDGE_KEY, JSON.stringify(v)) : localStorage.removeItem(BRIDGE_KEY); } catch { /* storage blocked */ } bridgeUp = null; },
};
let bridgeUp = null;                 // cached reachability: { ok, at }

function target() {
  if (!STATIC) return { base: "", headers: {} };
  const b = bridge.get();
  return b?.url && b?.code ? { base: b.url.replace(/\/$/, ""), headers: { authorization: `Bearer ${b.code}` }, code: b.code } : null;
}

async function req(method, url, body, t = target()) {
  const res = await fetch(t.base + url, { method, headers: { ...t.headers, ...(body ? { "content-type": "application/json" } : {}) }, body: body ? JSON.stringify(body) : undefined });
  let data = null;
  try { data = await res.json(); } catch { /* empty body */ }
  if (res.status === 401 && !STATIC && !url.startsWith("/api/login")) window.dispatchEvent(new CustomEvent("edge:auth"));
  if (!res.ok) throw Object.assign(new Error(data?.error || `Request failed (${res.status})`), { status: res.status });
  return data;
}

const httpApi = {
  session: () => req("GET", "/api/session"),
  login: (password) => req("POST", "/api/login", { password }),
  logout: () => req("POST", "/api/logout"),
  logoutAll: () => req("POST", "/api/logout-all"),
  regenerateBridge: () => req("POST", "/api/bridge/regenerate"),
  health: () => req("GET", "/api/health"),
  detect: () => req("POST", "/api/agent/detect"),
  overview: () => req("GET", "/api/overview"),
  strategies: () => req("GET", "/api/strategies"),
  strategy: (id) => req("GET", `/api/strategies/${encodeURIComponent(id)}`),
  sp: () => req("GET", "/api/sp"),
  montecarlo: (body) => req("POST", "/api/montecarlo", body),
  portfolio: (body) => req("POST", "/api/portfolio", body),
  conversations: () => req("GET", "/api/conversations"),
  conversation: (id) => req("GET", `/api/conversations/${encodeURIComponent(id)}`),
  deleteConversation: (id) => req("DELETE", `/api/conversations/${encodeURIComponent(id)}`),
  chat: (body) => req("POST", "/api/chat", body),
  cancel: (jobId) => req("POST", `/api/jobs/${encodeURIComponent(jobId)}/cancel`),
  experiments: () => req("GET", "/api/experiments"),
  createExperiment: (body) => req("POST", "/api/experiments", body),
  updateExperiment: (id, body) => req("PATCH", `/api/experiments/${encodeURIComponent(id)}`, body),
  duplicateExperiment: (id) => req("POST", `/api/experiments/${encodeURIComponent(id)}/duplicate`),
  deleteExperiment: (id) => req("DELETE", `/api/experiments/${encodeURIComponent(id)}`),
  runExperiment: (id) => req("POST", `/api/experiments/${encodeURIComponent(id)}/run`),
  history: () => req("GET", "/api/history"),
  settings: () => req("GET", "/api/settings"),
  saveSettings: (body) => req("PUT", "/api/settings", body),
  rebuild: () => req("POST", "/api/data/rebuild"),
};

/** Checks the saved bridge (cached 20 s). Returns { ok, error }. */
export async function testBridge(force = false) {
  const t = STATIC && target();
  if (!t) return { ok: false, error: "Not connected" };
  if (!force && bridgeUp && Date.now() - bridgeUp.at < 20000) return bridgeUp;
  try { const h = await req("GET", "/api/health", null, t); bridgeUp = { ok: true, at: Date.now(), health: h }; }
  catch (e) { bridgeUp = { ok: false, at: Date.now(), error: e.status === 401 ? "Wrong pairing code." : "Your computer is not reachable. Start Edge Lab on it (Start Edge Lab.bat) and check the address." }; }
  return bridgeUp;
}

const staticMod = STATIC ? import("./api-static.js") : null;
const NO_BRIDGE = new Set(["session", "login", "logout", "logoutAll"]);
export const api = !STATIC ? httpApi : new Proxy({}, {
  get: (_, k) => (k === "then" ? undefined : async (...a) => {
    if (!NO_BRIDGE.has(k) && target() && (await testBridge()).ok) {
      const out = await httpApi[k](...a);
      return k === "health" ? { ...out, bridge: { connected: true, url: target().base } } : out;
    }
    const out = await (await staticMod).api[k](...a);
    return k === "health" ? { ...out, bridge: { connected: false, url: target()?.base || null, error: bridgeUp?.error || null } } : out;
  }),
});

/** Follows an agent run. onEvent receives each normalised event; resolves at the end. */
export function stream(jobId, onEvent) {
  const t = target() || { base: "" };
  const q = t.code ? `?token=${encodeURIComponent(t.code)}` : "";
  return new Promise((resolve) => {
    const es = new EventSource(`${t.base}/api/jobs/${encodeURIComponent(jobId)}/stream${q}`);
    let ended = false;
    es.onmessage = (m) => {
      const e = JSON.parse(m.data); onEvent(e);
      if (e.type === "end") { ended = true; es.close(); resolve(); }
    };
    es.onerror = () => { es.close(); if (!ended) { onEvent({ type: "detached" }); resolve(); } };
  });
}
