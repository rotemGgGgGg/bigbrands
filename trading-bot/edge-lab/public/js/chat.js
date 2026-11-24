// Conversation UI shared by the welcome screen, the Research page and the side panel.
import { api, stream } from "./api.js";
import { $, esc, fmt, markdown, toast, errorBox } from "./util.js";
import { icon, logo } from "./icons.js";
import { state } from "./state.js";

const ACCEPT = ".txt,.md,.csv,.json,.py,.pine,.mq5,.log,.tsv";

/** Chat input. Returns { el, focus, setBusy, clear }. */
export function chatbar({ compact = false, placeholder = "Ask anything about your strategies…", onSubmit, showMeta = true, autofocus = false }) {
  const el = document.createElement("form");
  el.className = `chatbar${compact ? " compact" : ""}`;
  el.innerHTML = `
    <label class="sr-only" for="ta-${compact ? "c" : "f"}-${Math.random().toString(36).slice(2, 6)}">Message the research agent</label>
    <div class="attach-slot"></div>
    <textarea rows="1" placeholder="${esc(placeholder)}" aria-label="Message the research agent"></textarea>
    <div class="chatbar-row">
      <button type="button" class="icon-btn attach" title="Attach a text file (CSV, JSON, Python, Pine…)" aria-label="Attach file">${icon("paperclip", 16)}</button>
      <input type="file" accept="${ACCEPT}" hidden>
      ${showMeta ? `<div class="meta"><span class="status-dot ${agentDot()}"></span><span class="agent-label">${esc(agentLabel())}</span></div>` : ""}
      <div class="right">${compact ? "" : `<span class="kbd">↵ send</span><span class="kbd">⇧↵ new line</span>`}<button class="send" type="submit" aria-label="Send" disabled>${icon("arrowUp", 16, 2)}</button></div>
    </div>`;
  const ta = $("textarea", el), send = $(".send", el), file = $("input[type=file]", el), slot = $(".attach-slot", el);
  let attachment = null, busy = false, stopFn = null;
  const resize = () => { ta.style.height = "auto"; ta.style.height = `${Math.min(ta.scrollHeight, 260)}px`; send.disabled = !busy && !ta.value.trim(); };
  ta.addEventListener("input", resize);
  ta.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); el.requestSubmit(); } });
  $(".attach", el).addEventListener("click", () => file.click());
  file.addEventListener("change", () => {
    const f = file.files[0]; file.value = ""; if (!f) return;
    if (f.size > 200 * 1024) return toast("Attach text files up to 200 KB.", "err");
    const r = new FileReader();
    r.onload = () => { attachment = { name: f.name, content: String(r.result) }; slot.innerHTML = `<span class="attach-chip">${icon("file", 12)}${esc(f.name)}<button type="button" aria-label="Remove attachment">${icon("x", 12)}</button></span>`; $("button", slot).onclick = () => { attachment = null; slot.innerHTML = ""; }; };
    r.readAsText(f);
  });
  el.addEventListener("submit", (e) => {
    e.preventDefault();
    if (busy) { stopFn?.(); return; }
    const text = ta.value.trim(); if (!text) return;
    onSubmit(text, attachment);
  });
  const api_ = {
    el, focus: () => ta.focus(),
    clear() { ta.value = ""; attachment = null; slot.innerHTML = ""; resize(); },
    set(text) { ta.value = text; resize(); ta.focus(); },
    setBusy(b, onStop) { busy = b; stopFn = onStop; send.classList.toggle("stop", b); send.innerHTML = b ? icon("stop", 14) : icon("arrowUp", 16, 2); send.setAttribute("aria-label", b ? "Stop" : "Send"); send.disabled = b ? false : !ta.value.trim(); },
    refreshMeta() { const d = $(".status-dot", el), l = $(".agent-label", el); if (d) d.className = `status-dot ${agentDot()}`; if (l) l.textContent = agentLabel(); },
  };
  if (autofocus) setTimeout(() => ta.focus(), 50);
  state.chatbars.add(api_);
  return api_;
}

export function agentDot() { const a = state.health?.agent; return !a ? "" : a.available ? (state.busy ? "busy" : "ok") : "off"; }
export function agentLabel() {
  const h = state.health; if (!h) return "Connecting…";
  if (!h.agent.available) return "Agent offline · open Settings";
  const perm = h.permissions?.[h.settings.permission]?.label || h.settings.permission;
  const model = h.models?.find((m) => m.id === h.settings.model)?.label || "default model";
  return `Claude Code · ${model} · ${perm}`;
}

/** Sends a message (new conversation when conversationId is null). Returns { conversationId, jobId }. */
export async function sendMessage(text, { conversationId = null, attachment = null, context = state.context } = {}) {
  const body = { message: text, conversationId, context };
  if (attachment) body.attachment = attachment;
  return api.chat(body);
}

/** A rendered conversation with live streaming. */
export class Thread {
  constructor(host, { compact = false, onConversation } = {}) {
    this.host = host; this.compact = compact; this.onConversation = onConversation;
    this.conv = null; this.detached = new Set();
    host.innerHTML = `<div class="thread-wrap"><div class="thread"><div class="thread-inner"></div></div><div class="thread-input"></div></div>`;
    this.list = $(".thread-inner", host); this.scroller = $(".thread", host);
    this.bar = chatbar({ compact, placeholder: "Ask a follow-up…", onSubmit: (t, a) => this.send(t, a) });
    $(".thread-input", host).append(this.bar.el);
  }

  async load(id) {
    if (!id) { this.conv = null; this.list.innerHTML = this.compact ? `<div class="empty"><div class="ring">${logo(16)}</div><h3>Research agent</h3><p>Ask about the strategy on screen, or start a new test.</p></div>` : ""; this.bar.setBusy(false); return; }
    try { this.conv = await api.conversation(id); } catch (e) { this.list.innerHTML = errorBox("Could not open this conversation", e.message); return; }
    this.render();
    for (const m of this.conv.messages) if (m.status === "running" && m.jobId && !this.detached.has(m.id)) this.follow(m);
    this.scrollEnd(true);
  }

  render() {
    this.list.innerHTML = this.conv.messages.map((m) => (m.role === "user" ? `<div class="msg user" data-id="${m.id}">${esc(m.text)}</div>` : `<div class="msg assistant" data-id="${m.id}">${this.assistant(m)}</div>`)).join("");
    if (!this.conv.messages.length) this.list.innerHTML = "";
  }

  assistant(m) {
    if (m.status === "running" && this.detached.has(m.id) && !this.live?.has?.(m.id)) m = { ...m, status: "error", error: m.error || "This run is no longer attached. Reopen the conversation later to see its saved result." };
    const running = m.status === "running", steps = m.activity || [];
    const phase = running ? `<div class="phase"><span class="dots"><i></i><i></i><i></i></span><span class="shimmer">${esc(m.phaseLabel || "Thinking")}</span></div>` : "";
    const act = steps.length ? `<details class="activity" ${running ? "open" : ""}><summary>${icon(running ? "cpu" : "check", 13)}<span>${running ? "Working" : "Worked"} · ${steps.length} step${steps.length > 1 ? "s" : ""}</span><span class="chev">${icon("chevDown", 13)}</span></summary><div class="steps">${steps.map(stepHtml).join("")}</div></details>` : "";
    const body = m.text ? `<div class="md">${markdown(m.text)}${running ? '<span class="caret"></span>' : ""}</div>` : running && !steps.length ? "" : "";
    const err = m.status === "error" || m.error ? errorBox("The agent could not finish", hint(m.error)) : m.status === "cancelled" ? `<div class="caption">Stopped.</div>` : "";
    const denied = m.denied?.length ? `<div class="caption" style="margin-top:8px">Blocked by your permission level: ${esc([...new Set(m.denied)].join(", "))}. Change it in Settings.</div>` : "";
    const meta = !running && (m.durationMs || m.costUsd != null) ? `<div class="msg-meta">${m.durationMs ? `<span>${(m.durationMs / 1000).toFixed(1)}s</span>` : ""}${m.costUsd != null ? `<span>$${m.costUsd.toFixed(3)}</span>` : ""}${steps.length ? `<span>${steps.length} tool calls</span>` : ""}</div>` : "";
    return `<div class="agent-mark ${running ? "busy" : ""}">${logo(13)}</div><div style="min-width:0">${phase}${act}${body}${err}${denied}${meta}</div>`;
  }

  paint(m) {
    const node = this.list.querySelector(`[data-id="${m.id}"]`); if (!node) return;
    node.innerHTML = this.assistant(m);
    this.scrollEnd();
  }

  scrollEnd(force) {
    const s = this.scroller, near = s.scrollHeight - s.scrollTop - s.clientHeight < 160;
    if (force || near) requestAnimationFrame(() => { s.scrollTop = s.scrollHeight; });
  }

  async send(text, attachment) {
    if (state.health && !state.health.agent.available) { toast("The research agent is offline. Open Settings to connect Claude Code.", "err"); return; }
    this.bar.clear();
    try {
      const r = await sendMessage(text, { conversationId: this.conv?.id || null, attachment });
      if (!this.conv || this.conv.id !== r.conversationId) { this.conv = await api.conversation(r.conversationId); this.onConversation?.(this.conv); }
      else { this.conv.messages.push(r.userMsg, r.assistantMsg); }
      this.render(); this.scrollEnd(true);
      const m = this.conv.messages.find((x) => x.id === r.assistantMsg.id); this.follow(m);
    } catch (e) { toast(e.message, "err"); this.bar.set(text); }
  }

  follow(m) {
    m.activity = m.activity || []; m.text = m.text || ""; state.setBusy(this.conv.id, true);
    this.bar.setBusy(true, () => api.cancel(m.jobId).catch((e) => toast(e.message, "err")));
    let raf = 0; const paint = () => { if (!raf) raf = requestAnimationFrame(() => { raf = 0; this.paint(m); }); };
    m.text = ""; m.activity = [];
    stream(m.jobId, (e) => {
      if (e.type === "delta") m.text += e.text;
      else if (e.type === "phase") m.phaseLabel = e.label;
      else if (e.type === "tool") m.activity.push({ id: e.id, summary: e.summary, command: e.command, phase: e.phase, ok: null });
      else if (e.type === "tool_result") { const a = m.activity.find((x) => x.id === e.id); if (a) a.ok = e.ok; }
      else if (e.type === "error") { m.error = e.message; }
      else if (e.type === "result") { if (!m.text && e.text && e.ok) m.text = e.text; m.costUsd = e.costUsd; m.durationMs = e.durationMs; m.denied = e.denied; if (!e.ok) m.error = m.error || e.error; }
      else if (e.type === "cancelled") m.status = "cancelled";
      else if (e.type === "end") { if (m.status !== "cancelled") m.status = m.error ? "error" : "done"; }
      else if (e.type === "detached") { this.detached.add(m.id); m.status = "error"; m.error = m.error || "Lost the connection to this run. It may still finish on the server; reopen the conversation to see the saved result."; setTimeout(() => this.conv && this.load(this.conv.id), 800); }
      paint();
    }).then(() => { state.setBusy(this.conv?.id, false); this.bar.setBusy(false); paint(); });
  }
}

function stepHtml(s) {
  const cls = s.ok === null ? "run" : s.ok ? "ok" : "err";
  const ic = s.ok === null ? '<span class="dots" style="margin-top:4px"><i></i></span>' : icon(s.ok ? "check" : "x", 13);
  const kind = { analyzing: "search", coding: "code", running: "terminal" }[s.phase] || "cpu";
  return `<div class="step ${cls}"><span class="ic">${ic}</span><div><span>${icon(kind, 11)} ${esc(s.summary)}</span>${s.command && s.command !== s.summary ? `<code>${esc(s.command)}</code>` : ""}</div></div>`;
}

function hint(err) {
  const e = String(err || "Unknown error");
  if (/credit|usage|rate|429/i.test(e)) return `${e} — choose another model in Settings, or check your Claude plan.`;
  if (/not found|ENOENT/i.test(e)) return `${e} — install Claude Code or set CLAUDE_BIN, then re-check in Settings.`;
  if (/auth|login|401/i.test(e)) return `${e} — run "claude" once in a terminal to sign in.`;
  return e;
}
