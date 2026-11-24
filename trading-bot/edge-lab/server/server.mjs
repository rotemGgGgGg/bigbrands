// Edge Lab local server: static app + JSON API + Server-Sent Events for agent runs.
// Default: listens on 127.0.0.1 only, no login. With EDGE_LAB_PASSWORD every API call needs a session (see README).
// Always rejects unknown Host headers (DNS rebinding) and cross-origin writes.
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { execFile } from "node:child_process";
import { fileURLToPath } from "node:url";
import { ResearchData, summary } from "./lib/data.mjs";
import { simulate } from "./lib/montecarlo.mjs";
import { portfolio } from "./lib/portfolio.mjs";
import { Store, id } from "./lib/store.mjs";
import { Agent, PERMISSIONS, MODELS } from "./lib/agent.mjs";
import { Auth } from "./lib/auth.mjs";

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
// Optional local secrets file (gitignored): EDGE_LAB_PASSWORD, EDGE_LAB_API_KEY, ALLOWED_HOSTS, PORT, HOST, CLAUDE_BIN, PYTHON.
if (fs.existsSync(path.join(ROOT, ".env"))) process.loadEnvFile(path.join(ROOT, ".env"));
const PORT = +(process.env.PORT || 3007);
const HOST = process.env.HOST || "127.0.0.1";
const PASSWORD = process.env.EDGE_LAB_PASSWORD || "";
const API_KEY = process.env.EDGE_LAB_API_KEY || process.env.ANTHROPIC_API_KEY || "";
const EXTRA_HOSTS = (process.env.ALLOWED_HOSTS || "").split(",").map((h) => h.trim().toLowerCase()).filter(Boolean);
if (!["127.0.0.1", "localhost", "::1"].includes(HOST) && PASSWORD.length < 12) {
  console.error(`Refusing to listen on ${HOST} without a password. Set EDGE_LAB_PASSWORD (12+ characters), or leave HOST unset.`);
  process.exit(1);
}
const RESEARCH = path.resolve(process.env.RESEARCH_DIR || path.join(ROOT, "..", "research"));
const LAB = path.join(RESEARCH, "lab");
const REPO = path.resolve(RESEARCH, "..", "..");
const PY = process.env.PYTHON || (process.platform === "win32" ? "python" : "python3");

const data = new ResearchData(LAB);
const store = new Store(process.env.EDGE_LAB_STORE || path.join(ROOT, "store"));
const agent = new Agent({ workspace: RESEARCH });
const auth = new Auth(store, PASSWORD);
const jobs = new Map();                       // jobId -> { events, listeners:Set, status, cancel, conversationId, experimentId }
const DEFAULT_SETTINGS = { permission: "analyze", model: "", userName: "Rotem", billing: "subscription", maxBudgetUsd: 2 };

const settings = () => ({ ...DEFAULT_SETTINGS, ...store.read("settings", {}) });

// ---------------------------------------------------------------- helpers
const send = (res, code, body) => { res.writeHead(code, { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" }); res.end(JSON.stringify(body)); };
const fail = (res, code, message) => send(res, code, { error: message });

async function body(req) {
  let raw = ""; for await (const c of req) { raw += c; if (raw.length > 1.5e6) throw Object.assign(new Error("Request too large"), { code: 413 }); }
  if (!raw) return {};
  try { return JSON.parse(raw); } catch { throw Object.assign(new Error("Body must be JSON"), { code: 400 }); }
}

function allowed(req) {
  const host = String(req.headers.host || "").toLowerCase();
  const hosts = [`localhost:${PORT}`, `127.0.0.1:${PORT}`, ...EXTRA_HOSTS.flatMap((h) => (h.includes(":") ? [h] : [h, `${h}:${PORT}`]))];
  if (!hosts.includes(host)) return { ok: false, why: `Host "${host}" is not allowed. Add it with ALLOWED_HOSTS=${host.split(":")[0]} (and set EDGE_LAB_PASSWORD).` };
  const origin = req.headers.origin;
  if (req.method !== "GET" && req.method !== "HEAD" && origin && !hosts.some((h) => origin === `http://${h}` || origin === `https://${h}`)) return { ok: false, why: "Cross-origin request blocked." };
  return { ok: true };
}

const SECURITY_HEADERS = {
  "content-security-policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
  "x-frame-options": "DENY", "x-content-type-options": "nosniff", "referrer-policy": "no-referrer", "permissions-policy": "camera=(), microphone=(), geolocation=()",
};
const isHttps = (req) => req.headers["x-forwarded-proto"] === "https" || !!req.socket.encrypted;

const MIME = { ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".svg": "image/svg+xml", ".json": "application/json", ".png": "image/png", ".ico": "image/x-icon" };
function serveStatic(req, res, pathname) {
  const pub = path.join(ROOT, "public");
  let f = path.normalize(path.join(pub, decodeURIComponent(pathname)));
  if (!f.startsWith(pub)) return fail(res, 403, "Forbidden");
  if (!fs.existsSync(f) || fs.statSync(f).isDirectory()) f = path.join(pub, "index.html");
  res.writeHead(200, { "content-type": MIME[path.extname(f)] || "application/octet-stream", "cache-control": "no-cache" });
  fs.createReadStream(f).pipe(res);
}

// ---------------------------------------------------------------- agent jobs
function startJob({ prompt, conversationId, experimentId, displayText }) {
  const s = settings();
  const conv = store.read("conversations", []).find((c) => c.id === conversationId);
  const jobId = id("job");
  const job = { id: jobId, events: [], listeners: new Set(), status: "running", conversationId, experimentId, startedAt: Date.now(), text: "", activity: [] };
  jobs.set(jobId, job);

  const userMsg = { id: id("msg"), role: "user", text: displayText ?? prompt, at: new Date().toISOString() };
  const asst = { id: id("msg"), role: "assistant", text: "", status: "running", jobId, activity: [], at: new Date().toISOString() };
  store.update("conversations", [], (all) => {
    const c = all.find((x) => x.id === conversationId);
    c.messages.push(userMsg, asst); c.updatedAt = new Date().toISOString(); return all;
  });

  const push = (e) => {
    job.events.push(e);
    if (e.type === "delta") job.text += e.text;
    if (e.type === "tool") job.activity.push({ id: e.id, summary: e.summary, phase: e.phase, name: e.name, command: e.command, ok: null });
    if (e.type === "tool_result") { const a = job.activity.find((x) => x.id === e.id); if (a) a.ok = e.ok; }
    if (e.type === "init" && e.sessionId) store.update("conversations", [], (all) => { const c = all.find((x) => x.id === conversationId); if (c) c.sessionId = e.sessionId; return all; });
    if (e.type === "result") { job.result = e; if (!job.text && e.text && e.ok) job.text = e.text; }
    if (e.type === "error") job.error = e.message;
    if (e.type === "cancelled") job.cancelledFlag = true;
    if (e.type === "end") finishJob(job, asst.id);
    for (const l of job.listeners) l(e);
  };

  const billing = s.billing === "api" ? { mode: "api", apiKey: API_KEY, maxBudgetUsd: s.maxBudgetUsd } : { mode: "subscription" };
  const run = agent.run({ prompt, sessionId: conv?.sessionId, permission: s.permission, model: s.model, billing, onEvent: push });
  job.cancel = run.cancel;
  store.log("agent", `Agent run started`, { conversationId, experimentId, permission: s.permission });
  return { jobId, userMsg, assistantMsg: asst };
}

function finishJob(job, msgId) {
  job.status = job.cancelledFlag ? "cancelled" : job.error || job.result?.ok === false ? "error" : "done";
  const r = job.result || {};
  store.update("conversations", [], (all) => {
    const c = all.find((x) => x.id === job.conversationId); if (!c) return all;
    const m = c.messages.find((x) => x.id === msgId); if (!m) return all;
    Object.assign(m, { text: job.text || (r.ok ? r.text || "" : ""), status: job.status, error: job.error || r.error || null, activity: job.activity, costUsd: r.costUsd ?? null, durationMs: r.durationMs ?? Date.now() - job.startedAt, denied: r.denied || [] });
    c.updatedAt = new Date().toISOString(); return all;
  });
  if (job.experimentId) {
    store.update("experiments", [], (all) => {
      const x = all.find((e) => e.id === job.experimentId); if (!x) return all;
      x.status = job.status === "done" ? "completed" : "draft";
      x.result = { text: job.text || (r.ok ? r.text || "" : ""), metrics: parseMetrics(job.text || ""), at: new Date().toISOString(), status: job.status, error: job.error || null, conversationId: job.conversationId };
      x.history.push({ at: new Date().toISOString(), status: x.status, note: job.status === "done" ? "Agent run completed" : `Agent run ${job.status}` });
      return all;
    });
  }
  store.log("agent", `Agent run ${job.status}`, { conversationId: job.conversationId, experimentId: job.experimentId, costUsd: r.costUsd ?? null, error: job.error || null });
  setTimeout(() => jobs.delete(job.id), 10 * 60 * 1000).unref();
}

/** The agent ends a test report with a fenced json block; keep the last one that parses. */
function parseMetrics(text) {
  const blocks = [...text.matchAll(/```json\s*([\s\S]*?)```/g)].map((m) => m[1]);
  for (const b of blocks.reverse()) { try { const o = JSON.parse(b); if (o && typeof o === "object") return o; } catch { /* next */ } }
  return null;
}

function newConversation(title) {
  const c = { id: id("conv"), title: (title || "New research").slice(0, 80), createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(), sessionId: null, messages: [] };
  store.update("conversations", [], (all) => [c, ...all]);
  return c;
}

// ---------------------------------------------------------------- git history (fixed command, no user input)
function gitHistory() {
  return new Promise((resolve) => {
    execFile("git", ["-C", REPO, "log", "-n", "200", "--date=iso-strict", "--format=%H%x1f%ad%x1f%s", "--", path.relative(REPO, RESEARCH), path.join(path.relative(REPO, RESEARCH), "..", "pine")], { timeout: 15000 }, (err, out) => {
      if (err) return resolve([]);
      resolve(out.trim().split("\n").filter(Boolean).map((l) => { const [h, at, s] = l.split("\x1f"); return { id: h.slice(0, 10), at, type: "commit", title: s }; }));
    });
  });
}

// ---------------------------------------------------------------- routes
const routes = [];
const route = (method, pattern, fn) => routes.push({ method, re: new RegExp(`^${pattern.replace(/:(\w+)/g, "(?<$1>[^/]+)")}$`), fn });

route("GET", "/api/session", (req, res) => send(res, 200, { authRequired: auth.enabled, authenticated: !!auth.session(req) }));
route("POST", "/api/login", async (req, res) => {
  const b = await body(req), r = auth.login(req, res, String(b.password || ""), isHttps(req));
  if (!r.ok) return fail(res, r.code, r.error);
  store.log("security", "Signed in", { agent: String(req.headers["user-agent"] || "").slice(0, 80) }); send(res, 200, { ok: true });
});
route("POST", "/api/logout", (req, res) => { auth.logout(req, res); send(res, 200, { ok: true }); });
route("POST", "/api/logout-all", (req, res) => { auth.logoutAll(); auth.logout(req, res); store.log("security", "Signed out everywhere"); send(res, 200, { ok: true }); });

route("GET", "/api/health", async (req, res) => {
  const st = agent.status || (await agent.detect());
  send(res, 200, {
    agent: st, workspace: RESEARCH, settings: settings(), permissions: PERMISSIONS, models: MODELS, files: data.fileInfo(), runningJobs: [...jobs.values()].filter((j) => j.status === "running").length,
    security: { passwordProtected: auth.enabled, host: HOST, allowedHosts: EXTRA_HOSTS, sessions: Object.keys(store.read("sessions", {})).length },
    billing: { apiKeyConfigured: !!API_KEY },
  });
});
route("POST", "/api/agent/detect", async (req, res) => send(res, 200, await agent.detect()));

route("GET", "/api/overview", async (req, res) => {
  const d = data.load(), S = d.strategies, live = S.filter((s) => s.status === "LIVE");
  const best = [...live].filter((s) => s.oosT != null).sort((a, b) => b.oosT - a.oosT)[0];
  const exps = store.read("experiments", []);
  send(res, 200, {
    updated: d.meta.updated, theoriesTested: d.meta.theoriesTested, book: d.meta.book,
    counts: { total: S.length, live: live.length, watch: S.filter((s) => s.status === "WATCH").length, dead: S.filter((s) => s.status === "DEAD").length, experiments: exps.length },
    best: best ? summary(best) : null,
    liveExpectancy: live.length ? live.reduce((a, s) => a + (s.expectancy ?? 0), 0) / live.length : null,
    live: live.map(summary),
    recentExperiments: exps.slice(0, 5),
    activity: [...store.read("events", []).slice(0, 8), ...(await gitHistory()).slice(0, 8)].sort((a, b) => b.at.localeCompare(a.at)).slice(0, 8),
  });
});

route("GET", "/api/strategies", (req, res) => send(res, 200, data.load().strategies.map(summary)));
route("GET", "/api/strategies/:id", (req, res, p) => {
  const s = data.load().strategies.find((x) => x.id === p.id);
  return s ? send(res, 200, s) : fail(res, 404, "Strategy not found");
});
route("GET", "/api/sp", (req, res) => send(res, 200, data.load().sp || {}));

route("POST", "/api/montecarlo", async (req, res) => {
  const b = await body(req);
  let returns, label;
  if (b.weights) { const p = portfolio(data, b.weights, {}); return send(res, 200, { ...p.montecarlo, label: "Portfolio" }); }
  const s = data.series(b.strategy); if (!s) return fail(res, 404, "No trade series for that strategy");
  returns = s.r; label = b.strategy;
  const st = data.load().strategies.find((x) => x.id === b.strategy);
  const horizon = b.horizon || Math.round(st.perYear);
  send(res, 200, { ...simulate(returns, { ...b, horizon }), label, units: s.units });
});

route("POST", "/api/portfolio", async (req, res) => { const b = await body(req); send(res, 200, portfolio(data, b.weights || {}, b)); });

route("GET", "/api/conversations", (req, res) => send(res, 200, store.read("conversations", []).map(({ messages, ...c }) => ({ ...c, count: messages.length, preview: messages.find((m) => m.role === "user")?.text?.slice(0, 120) || "" }))));
route("GET", "/api/conversations/:id", (req, res, p) => {
  const c = store.read("conversations", []).find((x) => x.id === p.id);
  return c ? send(res, 200, c) : fail(res, 404, "Conversation not found");
});
route("DELETE", "/api/conversations/:id", (req, res, p) => { store.update("conversations", [], (a) => a.filter((c) => c.id !== p.id)); send(res, 200, { ok: true }); });

route("POST", "/api/chat", async (req, res) => {
  const b = await body(req);
  const text = String(b.message || "").trim();
  if (!text) return fail(res, 400, "Message is empty");
  if (text.length > 20000) return fail(res, 400, "Message is too long (20,000 characters max)");
  const st = agent.status || (await agent.detect());
  if (!st.available) return fail(res, 503, st.error || "Claude Code CLI is not available");
  if ([...jobs.values()].some((j) => j.status === "running" && j.conversationId === b.conversationId)) return fail(res, 409, "This conversation already has a run in progress");
  const conv = b.conversationId ? store.read("conversations", []).find((c) => c.id === b.conversationId) : newConversation(text);
  if (!conv) return fail(res, 404, "Conversation not found");
  const context = b.context ? `\n\n[Context from the Edge Lab screen: ${String(b.context).slice(0, 2000)}]` : "";
  const att = b.attachment && typeof b.attachment.content === "string" ? { name: String(b.attachment.name || "file").slice(0, 120), content: b.attachment.content.slice(0, 200000) } : null;
  const attached = att ? `\n\n[Attached file: ${att.name}]\n\`\`\`\n${att.content}\n\`\`\`` : "";
  const job = startJob({ prompt: text + attached + context, displayText: att ? `${text}\n\n📎 ${att.name}` : text, conversationId: conv.id });
  send(res, 200, { conversationId: conv.id, ...job });
});

route("GET", "/api/jobs/:id/stream", (req, res, p) => {
  const job = jobs.get(p.id);
  if (!job) return fail(res, 404, "Run not found or already finished");
  res.writeHead(200, { "content-type": "text/event-stream", "cache-control": "no-store", connection: "keep-alive" });
  const write = (e) => res.write(`data: ${JSON.stringify(e)}\n\n`);
  job.events.forEach(write);
  if (job.status !== "running") return res.end();
  const l = (e) => { write(e); if (e.type === "end") res.end(); };
  job.listeners.add(l);
  const ping = setInterval(() => res.write(": ping\n\n"), 15000);
  req.on("close", () => { job.listeners.delete(l); clearInterval(ping); });
});
route("POST", "/api/jobs/:id/cancel", (req, res, p) => {
  const job = jobs.get(p.id);
  if (!job || job.status !== "running") return fail(res, 404, "No running job with that id");
  job.cancel(); send(res, 200, { ok: true });
});

// Experiments: Draft -> Running -> Completed -> Reviewed -> Accepted / Rejected
const EXP_FIELDS = ["name", "hypothesis", "entry", "exit", "filters", "params", "notes"];
const NEXT = { draft: ["running"], running: ["completed", "draft"], completed: ["reviewed", "draft"], reviewed: ["accepted", "rejected", "draft"], accepted: [], rejected: ["draft"] };
route("GET", "/api/experiments", (req, res) => send(res, 200, store.read("experiments", [])));
route("POST", "/api/experiments", async (req, res) => {
  const b = await body(req); const d = data.load();
  const base = b.baseId ? d.strategies.find((s) => s.id === b.baseId) : null;
  if (b.baseId && !base) return fail(res, 404, "Base strategy not found");
  const snapshot = base ? { entry: base.entry || base.rule || "", exit: base.exit || "", filters: "", params: base.params ? JSON.stringify(base.params) : "" } : { entry: "", exit: "", filters: "", params: "" };
  const x = { id: id("exp"), createdAt: new Date().toISOString(), status: "draft", baseId: base?.id || null, baseName: base?.name || null, base: snapshot,
    name: String(b.name || (base ? `${base.name} variation` : "Untitled experiment")).slice(0, 120), hypothesis: String(b.hypothesis || ""),
    entry: b.entry ?? snapshot.entry, exit: b.exit ?? snapshot.exit, filters: b.filters ?? "", params: b.params ?? snapshot.params, notes: String(b.notes || ""),
    history: [{ at: new Date().toISOString(), status: "draft", note: base ? `Created from ${base.name}` : "Created" }], result: null };
  store.update("experiments", [], (a) => [x, ...a]); store.log("experiment", `Experiment created: ${x.name}`, { experimentId: x.id });
  send(res, 200, x);
});
route("POST", "/api/experiments/:id/duplicate", (req, res, p) => {
  const src = store.read("experiments", []).find((e) => e.id === p.id); if (!src) return fail(res, 404, "Experiment not found");
  const x = { ...structuredClone(src), id: id("exp"), name: `${src.name} (copy)`, createdAt: new Date().toISOString(), status: "draft", result: null, history: [{ at: new Date().toISOString(), status: "draft", note: `Duplicated from ${src.name}` }] };
  store.update("experiments", [], (a) => [x, ...a]); store.log("experiment", `Experiment duplicated: ${x.name}`, { experimentId: x.id }); send(res, 200, x);
});
route("PATCH", "/api/experiments/:id", async (req, res, p) => {
  const b = await body(req); let out, err;
  store.update("experiments", [], (all) => {
    const x = all.find((e) => e.id === p.id); if (!x) { err = [404, "Experiment not found"]; return all; }
    if (b.status && b.status !== x.status) {
      if (!NEXT[x.status].includes(b.status) || b.status === "running") { err = [400, `Cannot move from ${x.status} to ${b.status}`]; return all; }
      x.status = b.status; x.history.push({ at: new Date().toISOString(), status: b.status, note: String(b.note || "") });
    }
    if (x.status === "draft") {
      for (const f of EXP_FIELDS) if (f in b) x[f] = String(b[f]);
    } else if ("notes" in b) {
      x.notes = String(b.notes);
    }
    out = x; return all;
  });
  if (err) return fail(res, ...err);
  if (b.status) store.log("experiment", `Experiment ${b.status}: ${out.name}`, { experimentId: out.id });
  send(res, 200, out);
});
route("DELETE", "/api/experiments/:id", (req, res, p) => { store.update("experiments", [], (a) => a.filter((e) => e.id !== p.id)); send(res, 200, { ok: true }); });
route("POST", "/api/experiments/:id/run", async (req, res, p) => {
  const x = store.read("experiments", []).find((e) => e.id === p.id); if (!x) return fail(res, 404, "Experiment not found");
  if (x.status !== "draft") return fail(res, 400, "Only a draft can be run");
  const st = agent.status || (await agent.detect()); if (!st.available) return fail(res, 503, st.error || "Claude Code CLI is not available");
  if (settings().permission === "read") return fail(res, 400, "Running an experiment needs the Analyze or Build permission level (Settings).");
  const changed = EXP_FIELDS.filter((f) => ["entry", "exit", "filters", "params"].includes(f) && (x[f] || "") !== (x.base[f] || ""));
  const prompt = [`Run this Edge Lab experiment and report the result.`, `Experiment: ${x.name}`, x.baseName ? `Base strategy: ${x.baseName} (id ${x.baseId}). Keep the original strategy files unchanged; write the variation as a new script.` : `New strategy.`,
    x.hypothesis && `Hypothesis: ${x.hypothesis}`, `Entry: ${x.entry || "(as base)"}`, `Exit: ${x.exit || "(as base)"}`, x.filters && `Filters: ${x.filters}`, x.params && `Parameters: ${x.params}`,
    changed.length ? `Changed vs base: ${changed.join(", ")}.` : `No rule changes vs base: reproduce the base result.`, x.notes && `Notes: ${x.notes}`,
    `Use the research gates (choose on 2012-19, judge 2020-26 once, costs, random twin) and end with the json metrics block.`].filter(Boolean).join("\n");
  const conv = newConversation(`Experiment: ${x.name}`);
  store.update("experiments", [], (all) => { const e = all.find((y) => y.id === x.id); e.status = "running"; e.history.push({ at: new Date().toISOString(), status: "running", note: "Sent to the research agent" }); e.conversationId = conv.id; return all; });
  const job = startJob({ prompt, conversationId: conv.id, experimentId: x.id });
  send(res, 200, { conversationId: conv.id, ...job });
});

route("GET", "/api/history", async (req, res) => {
  const convs = store.read("conversations", []).map((c) => ({ id: c.id, at: c.createdAt, type: "conversation", title: c.title, conversationId: c.id }));
  const all = [...store.read("events", []), ...convs, ...(await gitHistory())].sort((a, b) => b.at.localeCompare(a.at));
  send(res, 200, all);
});

route("GET", "/api/settings", (req, res) => send(res, 200, settings()));
route("PUT", "/api/settings", async (req, res) => {
  const b = await body(req), cur = settings();
  if (b.permission && !PERMISSIONS[b.permission]) return fail(res, 400, "Unknown permission level");
  if ("model" in b && !MODELS.some((m) => m.id === b.model)) return fail(res, 400, "Unknown model");
  if (b.billing && !["subscription", "api"].includes(b.billing)) return fail(res, 400, "Unknown billing mode");
  if (b.billing === "api" && !API_KEY) return fail(res, 400, "No API key on the server. Start it with EDGE_LAB_API_KEY set (see README); the key never goes through the browser.");
  const budget = "maxBudgetUsd" in b ? Math.min(Math.max(+b.maxBudgetUsd || 0, 0.1), 50) : cur.maxBudgetUsd;
  const next = { ...cur, ...(b.permission && { permission: b.permission }), ...("model" in b && { model: b.model }), ...(b.billing && { billing: b.billing }), maxBudgetUsd: budget };
  store.write("settings", next); store.log("settings", `Agent settings changed`, { permission: next.permission, model: next.model || "default", billing: next.billing });
  send(res, 200, next);
});

// Rebuild research/lab/data.json from the registry script (fixed command).
route("POST", "/api/data/rebuild", (req, res) => {
  execFile(PY, ["build.py"], { cwd: LAB, timeout: 120000 }, (err, stdout, stderr) => {
    if (err) return fail(res, 500, `build.py failed: ${(stderr || err.message).trim().slice(-500)}`);
    store.log("data", "Lab data rebuilt", {}); send(res, 200, { ok: true, output: stdout.trim() });
  });
});

// ---------------------------------------------------------------- server
const server = http.createServer(async (req, res) => {
  try {
    for (const [k, v] of Object.entries(SECURITY_HEADERS)) res.setHeader(k, v);
    const gate = allowed(req);
    if (!gate.ok) return fail(res, 403, gate.why);
    const url = new URL(req.url, `http://${req.headers.host}`);
    if (url.pathname.startsWith("/api/")) {
      if (!["/api/session", "/api/login"].includes(url.pathname) && !auth.session(req)) return fail(res, 401, "Sign in required.");
      for (const r of routes) {
        const m = r.method === req.method && url.pathname.match(r.re);
        if (m) return await r.fn(req, res, m.groups || {}, url);
      }
      return fail(res, 404, "Unknown endpoint");
    }
    serveStatic(req, res, url.pathname);
  } catch (e) {
    console.error(e);
    if (!res.headersSent) fail(res, e.code && Number.isInteger(e.code) ? e.code : 500, e.message);
  }
});

server.on("error", (e) => { console.error(e.code === "EADDRINUSE" ? `Port ${PORT} is in use. Start with PORT=3008 npm start.` : e.message); process.exit(1); });
server.listen(PORT, HOST, async () => {
  const st = await agent.detect();
  console.log(`Edge Lab  →  http://localhost:${PORT}${HOST !== "127.0.0.1" ? `  (listening on ${HOST})` : ""}`);
  console.log(`Access    →  ${auth.enabled ? "password required" : "this computer only, no login"}${EXTRA_HOSTS.length ? ` · extra hosts: ${EXTRA_HOSTS.join(", ")}` : ""}`);
  console.log(`Billing   →  ${settings().billing === "api" ? (API_KEY ? "Claude API key (per-run cap)" : "API selected but no key set") : "your Claude subscription (Claude Code sign-in)"}`);
  console.log(`Workspace →  ${RESEARCH}`);
  console.log(`Agent     →  ${st.available ? `Claude Code ${st.version}` : st.error}`);
});
