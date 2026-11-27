// Conversation UI shared by the welcome screen, the Research page and the side panel.
import { api, stream, uploadUrl } from "./api.js";
import { $, esc, fmt, markdown, toast, errorBox } from "./util.js";
import { icon, logo } from "./icons.js";
import { state } from "./state.js";

const ACCEPT = ".txt,.md,.csv,.json,.py,.pine,.mq5,.log,.tsv,image/png,image/jpeg,image/webp,image/gif";
const IMG = /^image\/(png|jpeg|webp|gif)$/;
export const COMMANDS = [
  { cmd: "/rotem", hint: "Answer short, straight to the point, explained simply (stays on for this chat; /rotem off)" },
  { cmd: "/usage", hint: "Save usage: fewer tokens and tool calls (stays on; /usage off)" },
  { cmd: "/loop", hint: "/loop 5 <task> · works on its own for up to N rounds (max 10) until done" },
];

/** Chat input. Returns { el, focus, setBusy, clear, set, setModes }. */
export function chatbar({ compact = false, placeholder = "Ask anything about your strategies…", onSubmit, showMeta = true, autofocus = false }) {
  const el = document.createElement("form");
  el.className = `chatbar${compact ? " compact" : ""}`;
  el.innerHTML = `
    <div class="slash-menu" hidden role="listbox"></div>
    <div class="attach-slot"></div>
    <textarea rows="1" placeholder="${esc(placeholder)}" aria-label="Message the research agent"></textarea>
    <div class="chatbar-row">
      <button type="button" class="icon-btn attach" title="Attach images or a text file (or paste an image)" aria-label="Attach">${icon("paperclip", 16)}</button>
      <input type="file" accept="${ACCEPT}" multiple hidden>
      <button type="button" class="model-chip" title="Model for the agent">${icon("cpu", 12)}<span></span>${icon("chevDown", 11)}</button>
      <span class="mode-chips"></span>
      ${showMeta ? `<div class="meta"><span class="status-dot ${agentDot()}"></span><span class="agent-label">${esc(agentLabel())}</span></div>` : ""}
      <div class="right">${compact ? "" : `<span class="kbd">/ commands</span><span class="kbd">↵ send</span>`}<button class="send" type="submit" aria-label="Send" disabled>${icon("arrowUp", 16, 2)}</button></div>
    </div>
    <div class="model-menu" hidden></div>`;
  const ta = $("textarea", el), send = $(".send", el), file = $("input[type=file]", el), slot = $(".attach-slot", el);
  const menu = $(".slash-menu", el), mchip = $(".model-chip", el), mmenu = $(".model-menu", el);
  let attachment = null, images = [], busy = false, stopFn = null, sel = 0;
  const canSend = () => !!(ta.value.trim() || images.length);
  const resize = () => { ta.style.height = "auto"; ta.style.height = `${Math.min(ta.scrollHeight, 260)}px`; send.disabled = !busy && !canSend(); };

  const paintSlot = () => {
    slot.innerHTML = (attachment ? `<span class="attach-chip" data-k="file">${icon("file", 12)}${esc(attachment.name)}<button type="button" aria-label="Remove">${icon("x", 12)}</button></span>` : "") +
      images.map((im, i) => `<span class="img-chip" data-i="${i}"><img src="${im.data}" alt="${esc(im.name)}"><button type="button" aria-label="Remove image">${icon("x", 11)}</button></span>`).join("");
    slot.querySelectorAll("button").forEach((b) => (b.onclick = () => { const c = b.parentElement; if (c.dataset.k === "file") attachment = null; else images.splice(+c.dataset.i, 1); paintSlot(); resize(); }));
  };
  const addFiles = (list) => {
    for (const f of list) {
      if (IMG.test(f.type)) {
        if (images.length >= 4) { toast("Up to 4 images per message.", "err"); break; }
        if (f.size > 5 * 1024 * 1024) { toast(`${f.name}: images up to 5 MB.`, "err"); continue; }
        const r = new FileReader(); r.onload = () => { images.push({ name: f.name || "pasted.png", type: f.type, data: String(r.result) }); paintSlot(); resize(); }; r.readAsDataURL(f);
      } else {
        if (f.size > 200 * 1024) { toast("Attach text files up to 200 KB.", "err"); continue; }
        const r = new FileReader(); r.onload = () => { attachment = { name: f.name, content: String(r.result) }; paintSlot(); }; r.readAsText(f);
      }
    }
  };

  // Slash-command menu
  const matches = () => { const m = ta.value.match(/^\/(\w*)$/); return m ? COMMANDS.filter((c) => c.cmd.startsWith("/" + m[1].toLowerCase())) : []; };
  const paintMenu = () => {
    const list = matches(); menu.hidden = !list.length; if (!list.length) return;
    sel = Math.min(sel, list.length - 1);
    menu.innerHTML = list.map((c, i) => `<button type="button" class="${i === sel ? "on" : ""}" data-cmd="${c.cmd}"><b>${c.cmd}</b><span>${esc(c.hint)}</span></button>`).join("");
    menu.querySelectorAll("button").forEach((b) => (b.onmousedown = (e) => { e.preventDefault(); pick(b.dataset.cmd); }));
  };
  const pick = (cmd) => { ta.value = cmd + (cmd === "/loop" ? " 5 " : " "); menu.hidden = true; resize(); ta.focus(); };

  ta.addEventListener("input", () => { resize(); paintMenu(); });
  ta.addEventListener("keydown", (e) => {
    if (!menu.hidden) {
      const list = matches();
      if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); sel = (sel + (e.key === "ArrowDown" ? 1 : list.length - 1)) % list.length; paintMenu(); return; }
      if (e.key === "Tab" || (e.key === "Enter" && !e.shiftKey)) { e.preventDefault(); pick(list[sel].cmd); return; }
      if (e.key === "Escape") { menu.hidden = true; return; }
    }
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); el.requestSubmit(); }
  });
  ta.addEventListener("paste", (e) => { const fs = [...(e.clipboardData?.files || [])].filter((f) => IMG.test(f.type)); if (fs.length) { e.preventDefault(); addFiles(fs); } });
  el.addEventListener("dragover", (e) => { e.preventDefault(); el.classList.add("drag"); });
  el.addEventListener("dragleave", () => el.classList.remove("drag"));
  el.addEventListener("drop", (e) => { e.preventDefault(); el.classList.remove("drag"); addFiles([...(e.dataTransfer?.files || [])]); });
  $(".attach", el).addEventListener("click", () => file.click());
  file.addEventListener("change", () => { addFiles([...file.files]); file.value = ""; });

  // Model switch
  mchip.addEventListener("click", () => {
    const h = state.health; if (!h?.models?.length) return;
    mmenu.innerHTML = h.models.map((m) => `<button type="button" data-id="${esc(m.id)}" class="${m.id === h.settings.model ? "on" : ""}">${esc(m.label)}${m.note ? `<small>${esc(m.note)}</small>` : ""}</button>`).join("");
    mmenu.hidden = !mmenu.hidden;
    mmenu.querySelectorAll("button").forEach((b) => (b.onclick = async () => {
      mmenu.hidden = true;
      try { const s = await api.saveSettings({ model: b.dataset.id }); state.setHealth({ ...state.health, settings: { ...state.health.settings, ...(s?.settings || s || {}), model: b.dataset.id } }); toast(`Model: ${b.textContent}`); }
      catch (err) { toast(err.message, "err"); }
    }));
  });
  document.addEventListener("click", (e) => { if (!el.contains(e.target)) { mmenu.hidden = true; menu.hidden = true; } });

  el.addEventListener("submit", (e) => {
    e.preventDefault();
    if (busy) { stopFn?.(); return; }
    if (!canSend()) return;
    onSubmit(ta.value.trim(), attachment, images.map(({ name, type, data }) => ({ name, type, data })));
  });
  const api_ = {
    el, focus: () => ta.focus(),
    clear() { ta.value = ""; attachment = null; images = []; paintSlot(); resize(); menu.hidden = true; },
    set(text) { ta.value = text; resize(); ta.focus(); },
    setModes(modes = []) { $(".mode-chips", el).innerHTML = modes.map((m) => `<span class="mode-chip" title="Mode on for this chat. Send /${m} off to turn it off.">/${esc(m)}</span>`).join(""); },
    setBusy(b, onStop) { busy = b; stopFn = onStop; send.classList.toggle("stop", b); send.innerHTML = b ? icon("stop", 14) : icon("arrowUp", 16, 2); send.setAttribute("aria-label", b ? "Stop" : "Send"); send.disabled = b ? false : !canSend(); },
    refreshMeta() {
      const d = $(".status-dot", el), l = $(".agent-label", el); if (d) d.className = `status-dot ${agentDot()}`; if (l) l.textContent = agentLabel();
      const h = state.health; $("span", mchip).textContent = h?.models ? (h.models.find((m) => m.id === h.settings?.model)?.label || "Default") : "Model";
    },
  };
  api_.refreshMeta();
  if (autofocus) setTimeout(() => ta.focus(), 50);
  state.chatbars.add(api_);
  return api_;
}

/** Usage strip: 5-hour and weekly plan limits (from Claude Code) + how full this chat's context is. */
export function usageHtml(u, convUsage) {
  const lim = u?.limits?.info?.unifiedWindows || {};
  const at = (t) => { if (!t) return ""; const d = new Date(t * (t < 1e12 ? 1000 : 1)); return d.toLocaleString([], d - Date.now() > 20 * 3600e3 ? { weekday: "short", hour: "2-digit", minute: "2-digit" } : { hour: "2-digit", minute: "2-digit" }); };
  const bar = (label, pct, title) => { const p = Math.max(0, Math.min(100, pct)); return `<span class="u-item" title="${esc(title)}"><span class="u-l">${label}</span><span class="u-track"><b class="${p >= 85 ? "hot" : p >= 60 ? "warm" : ""}" style="width:${p}%"></b></span><span class="u-v">${Math.round(p)}%</span></span>`; };
  const parts = [];
  const five = lim.five_hour, week = lim.seven_day;
  if (five?.utilization != null) parts.push(bar("5h", five.utilization * 100, `5-hour limit · resets ${at(five.resetsAt)}`));
  if (week?.utilization != null) parts.push(bar("Week", week.utilization * 100, `Weekly limit · resets ${at(week.resetsAt)}`));
  if (convUsage?.contextTokens && convUsage?.contextWindow) parts.push(bar("Chat", (100 * convUsage.contextTokens) / convUsage.contextWindow, `This chat uses ${Math.round(convUsage.contextTokens / 1000)}k of ${Math.round(convUsage.contextWindow / 1000)}k tokens of context. Start a new chat when it gets high.`));
  if (!parts.length) return `<span class="u-empty">${icon("gauge", 12)} Usage shows after the first reply</span>`;
  const reset = five?.resetsAt ? `<span class="u-reset">5h resets ${at(five.resetsAt)}</span>` : "";
  return `${icon("gauge", 12)}${parts.join("")}${reset}`;
}

/** Inline rename: swaps el for an input; Enter saves, Esc cancels. */
export function editTitle(el, conv, onSaved) {
  if (!conv?.id || el.querySelector("input")) return;
  const old = conv.title, inp = document.createElement("input");
  inp.className = "title-input"; inp.value = old; inp.maxLength = 80; inp.setAttribute("aria-label", "Chat name");
  el.replaceChildren(inp); inp.focus(); inp.select();
  let done = false;
  const finish = async (save) => {
    if (done) return; done = true;
    const v = inp.value.trim();
    if (save && v && v !== old) { try { const c = await api.updateConversation(conv.id, { title: v }); conv.title = c.title; onSaved?.(c); } catch (e) { toast(e.message, "err"); } }
    el.textContent = conv.title;
  };
  inp.onkeydown = (e) => { if (e.key === "Enter") { e.preventDefault(); finish(true); } if (e.key === "Escape") finish(false); e.stopPropagation(); };
  inp.onblur = () => finish(true);
}

export function agentDot() { const a = state.health?.agent; return !a ? "" : a.available ? (state.busy ? "busy" : "ok") : "off"; }
export function agentLabel() {
  const h = state.health; if (!h) return "Connecting…";
  if (!h.agent.available) return "Agent offline · open Settings";
  const perm = h.permissions?.[h.settings.permission]?.label || h.settings.permission;
  return `${perm} · ${h.settings.billing === "api" ? "API key" : "subscription"}`;
}

/** Sends a message (new conversation when conversationId is null). Returns { conversationId, jobId }. */
export async function sendMessage(text, { conversationId = null, attachment = null, images = [], context = state.context } = {}) {
  const body = { message: text, conversationId, context };
  if (attachment) body.attachment = attachment;
  if (images?.length) body.images = images;
  return api.chat(body);
}

/** A rendered conversation with live streaming. */
export class Thread {
  constructor(host, { compact = false, onConversation } = {}) {
    this.host = host; this.compact = compact; this.onConversation = onConversation;
    this.conv = null; this.detached = new Set();
    host.innerHTML = `<div class="thread-wrap">${compact ? "" : `<div class="thread-head" hidden><span class="th-title" title="Click to rename"></span><button class="icon-btn th-rename" title="Rename" aria-label="Rename chat">${icon("edit", 14)}</button><button class="icon-btn th-pin" title="Pin to top" aria-label="Pin chat">${icon("pin", 14)}</button></div>`}<div class="thread"><div class="thread-inner"></div></div><div class="thread-input"><div class="usage-strip"></div></div></div>`;
    this.list = $(".thread-inner", host); this.scroller = $(".thread", host); this.usageEl = $(".usage-strip", host);
    this.bar = chatbar({ compact, placeholder: "Ask a follow-up…", onSubmit: (t, a, im) => this.send(t, a, im) });
    $(".thread-input", host).append(this.bar.el);
    const head = $(".thread-head", host);
    if (head) {
      const rename = () => editTitle($(".th-title", head), this.conv, (c) => this.onConversation?.(this.conv));
      $(".th-title", head).onclick = rename; $(".th-rename", head).onclick = rename;
      $(".th-pin", head).onclick = async () => {
        if (!this.conv || this.conv.main) return;
        try { const c = await api.updateConversation(this.conv.id, { pinned: !this.conv.pinned }); this.conv.pinned = c.pinned; this.paintHead(); this.onConversation?.(this.conv); } catch (e) { toast(e.message, "err"); }
      };
    }
    this.refreshUsage();
  }

  paintHead() {
    const head = $(".thread-head", this.host); this.bar.setModes(this.conv?.modes || []);
    if (!head) return;
    head.hidden = !this.conv; if (!this.conv) return;
    head.classList.toggle("is-main", !!this.conv.main);
    $(".th-title", head).textContent = this.conv.title;
    const pin = $(".th-pin", head); pin.hidden = !!this.conv.main; pin.classList.toggle("on", !!this.conv.pinned); pin.title = this.conv.pinned ? "Unpin" : "Pin to top";
  }

  async refreshUsage(u) {
    try { this.usage = u || (await api.usage()); } catch { this.usage = null; }
    const last = [...(this.conv?.messages || [])].reverse().find((m) => m.usage)?.usage || this.conv?.lastUsage;
    this.usageEl.innerHTML = usageHtml(this.usage, last);
  }

  async load(id) {
    if (!id) { this.conv = null; this.paintHead(); this.refreshUsage(); this.list.innerHTML = this.compact ? `<div class="empty"><div class="ring">${logo(16)}</div><h3>Research agent</h3><p>Ask about the strategy on screen, or start a new test.</p></div>` : ""; this.bar.setBusy(false); return; }
    try { this.conv = await api.conversation(id); } catch (e) { this.list.innerHTML = errorBox("Could not open this conversation", e.message); return; }
    this.render(); this.paintHead(); this.refreshUsage();
    for (const m of this.conv.messages) if (m.status === "running" && m.jobId && !this.detached.has(m.id)) this.follow(m);
    this.scrollEnd(true);
  }

  render() {
    this.list.innerHTML = this.conv.messages.map((m) => (m.role === "user" ? `<div class="msg user" data-id="${m.id}">${userTags(m)}${(m.images || []).map((im) => `<a href="${uploadUrl(im.file)}" target="_blank" rel="noopener"><img class="msg-img" src="${uploadUrl(im.file)}" alt="${esc(im.name)}" loading="lazy"></a>`).join("")}${esc(m.text)}</div>` : `<div class="msg assistant" data-id="${m.id}">${this.assistant(m)}</div>`)).join("");
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
    const meta = !running && (m.durationMs || m.costUsd != null) ? `<div class="msg-meta">${m.durationMs ? `<span>${(m.durationMs / 1000).toFixed(1)}s</span>` : ""}${m.costUsd != null ? `<span>$${m.costUsd.toFixed(3)}</span>` : ""}${steps.length ? `<span>${steps.length} tool calls</span>` : ""}${m.iterations ? `<span>loop · ${m.iterations} rounds</span>` : ""}${m.usage?.contextTokens ? `<span>${Math.round(m.usage.contextTokens / 1000)}k context</span>` : ""}</div>` : "";
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

  async send(text, attachment, images = []) {
    if (state.health && !state.health.agent.available) { toast("The research agent is offline. Open Settings to connect Claude Code.", "err"); return; }
    this.bar.clear();
    try {
      const r = await sendMessage(text, { conversationId: this.conv?.id || null, attachment, images });
      if (r.commandOnly) { if (this.conv) this.conv.modes = r.modes; this.bar.setModes(r.modes); toast(r.modes.length ? `On for this chat: ${r.modes.map((m) => "/" + m).join(" ")}` : "Modes off"); return; }
      if (!this.conv || this.conv.id !== r.conversationId) { this.conv = await api.conversation(r.conversationId); this.onConversation?.(this.conv); }
      else { this.conv.messages.push(r.userMsg, r.assistantMsg); this.conv.modes = r.modes; }
      this.paintHead();
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
      else if (e.type === "result") { if (!m.text && e.text && e.ok) m.text = e.text; m.costUsd = e.costUsd; m.durationMs = e.durationMs; m.denied = e.denied; if (e.usage) m.usage = e.usage; if (!e.ok) m.error = m.error || e.error; }
      else if (e.type === "limits") { this.refreshUsage({ ...(this.usage || {}), limits: { info: e.info } }); }
      else if (e.type === "cancelled") m.status = "cancelled";
      else if (e.type === "end") { if (m.status !== "cancelled") m.status = m.error ? "error" : "done"; }
      else if (e.type === "detached") { this.detached.add(m.id); m.status = "error"; m.error = m.error || "Lost the connection to this run. It may still finish on the server; reopen the conversation to see the saved result."; setTimeout(() => this.conv && this.load(this.conv.id), 800); }
      paint();
    }).then(() => { state.setBusy(this.conv?.id, false); this.bar.setBusy(false); paint(); this.refreshUsage(); });
  }
}

function userTags(m) {
  const t = [...(m.modes || []).map((x) => "/" + x), m.loop ? `/loop ${m.loop}` : ""].filter(Boolean);
  return t.length ? `<div class="msg-tags">${t.map((x) => `<span>${esc(x)}</span>`).join("")}</div>` : "";
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
