// Opening screen: greeting, the main chatbar and suggested prompts. Submitting starts a real conversation
// with the research agent and moves into the workspace.
import { $, esc, toast } from "../util.js";
import { icon, logo } from "../icons.js";
import { state } from "../state.js";
import { chatbar, sendMessage } from "../chat.js";

const PROMPTS = [
  ["Analyze my latest strategy.", "sparkle"],
  ["Compare all NQ strategies.", "compare"],
  ["Run a Monte Carlo simulation.", "dice"],
  ["Find the best performing entry conditions.", "search"],
  ["Test a volatility filter.", "flask"],
  ["Investigate drawdown behavior.", "strategies"],
];

export default async function welcome(main, _params, { refreshHealth }) {
  const name = state.health?.settings?.userName || "Rotem";
  main.innerHTML = `
    <div class="welcome-screen">
      <div class="welcome-top"><span class="brand-mark" style="width:26px;height:26px;border-radius:8px;border:1px solid var(--border);display:grid;place-items:center">${logo(14)}</span>
        <span style="font-weight:500">Edge Lab</span>
        <div class="right"><a class="btn ghost sm" href="#overview">Open workspace ${icon("arrowRight", 13)}</a></div></div>
      <div class="greeting"><h1>Hello, <em>Mr. ${esc(name)}.</em></h1><p>Your research environment is ready.</p></div>
      <div id="bar-host" style="width:min(720px,100%)"></div>
      <div id="offline" style="width:min(720px,100%);margin-top:12px"></div>
      <div class="chips">${PROMPTS.map(([p, ic]) => `<button class="chip" type="button" data-p="${esc(p)}">${icon(ic, 13)}${esc(p)}</button>`).join("")}</div>
      <div class="welcome-foot">Runs locally · Claude Code works inside your research folder · <span class="kbd">⌘K</span> focus</div>
    </div>`;
  const screen = $(".welcome-screen", main);
  const bar = chatbar({ onSubmit: (t, a) => go(t, a), autofocus: true });
  bar.el.style.width = "100%";
  $("#bar-host", main).append(bar.el);
  main.querySelectorAll(".chip").forEach((c) => c.addEventListener("click", () => go(c.dataset.p)));

  const paintOffline = () => {
    const a = state.health?.agent;
    $("#offline", main).innerHTML = a && !a.available ? `<div class="err-box"><b>The research agent is offline.</b> ${esc(a.error || "")} You can still browse the workspace. <a href="#settings">Open Settings</a></div>` : "";
  };
  paintOffline(); state.on(paintOffline);

  async function go(text, attachment) {
    if (!state.health) await refreshHealth();
    if (!state.health?.agent?.available) { paintOffline(); toast("The research agent is offline.", "err"); bar.set(text); return; }
    bar.setBusy(true); bar.clear();
    try {
      const r = await sendMessage(text, { attachment });
      screen.classList.add("leaving");
      setTimeout(() => { location.hash = `#research/${r.conversationId}`; }, 380);
    } catch (e) { bar.setBusy(false); bar.set(text); toast(e.message, "err"); }
  }
  return () => state.listeners.delete(paintOffline);
}
