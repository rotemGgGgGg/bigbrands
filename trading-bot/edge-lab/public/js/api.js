// Thin client for the local Edge Lab server.
async function req(method, url, body) {
  const res = await fetch(url, { method, headers: body ? { "content-type": "application/json" } : {}, body: body ? JSON.stringify(body) : undefined });
  let data = null;
  try { data = await res.json(); } catch { /* empty body */ }
  if (res.status === 401 && !url.startsWith("/api/login")) window.dispatchEvent(new CustomEvent("edge:auth"));
  if (!res.ok) throw Object.assign(new Error(data?.error || `Request failed (${res.status})`), { status: res.status });
  return data;
}

export const api = {
  session: () => req("GET", "/api/session"),
  login: (password) => req("POST", "/api/login", { password }),
  logout: () => req("POST", "/api/logout"),
  logoutAll: () => req("POST", "/api/logout-all"),
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

/** Follows an agent run. onEvent receives each normalised event; resolves at the end. */
export function stream(jobId, onEvent) {
  return new Promise((resolve) => {
    const es = new EventSource(`/api/jobs/${encodeURIComponent(jobId)}/stream`);
    let ended = false;
    es.onmessage = (m) => {
      const e = JSON.parse(m.data); onEvent(e);
      if (e.type === "end") { ended = true; es.close(); resolve(); }
    };
    es.onerror = () => { es.close(); if (!ended) { onEvent({ type: "detached" }); resolve(); } };
  });
}
