// Research History: git commits of the research folder, agent runs, experiments, conversations and settings changes.
import { api } from "../api.js";
import { $, $$, esc, fmt, skeleton, emptyState, debounce } from "../util.js";
import { icon } from "../icons.js";

const TYPES = [["all", "All"], ["commit", "Commits"], ["experiment", "Experiments"], ["agent", "Agent runs"], ["conversation", "Conversations"], ["settings", "Settings"]];
const IC = { commit: "git", experiment: "flask", agent: "cpu", conversation: "chat", settings: "settings", data: "database" };

export default async function historyView(main) {
  main.innerHTML = skeleton([60, 400]);
  const all = await api.history();
  let type = "all", q = "";
  main.innerHTML = `
  <div class="page">
    <div class="page-head fade-in"><div><h1>Research History</h1><p>${fmt.n(all.length)} events · commits come from the research folder's git log</p></div></div>
    <div class="row fade-in d1" style="margin-bottom:18px;gap:10px">
      <div class="search" style="width:280px"><label class="sr-only" for="hq">Search history</label>${icon("search", 14)}<input id="hq" class="input" placeholder="Search…"></div>
      <div class="seg" role="group" aria-label="Event type">${TYPES.map(([k, l]) => `<button data-t="${k}" aria-pressed="${k === type}">${l}</button>`).join("")}</div>
    </div>
    <div class="timeline fade-in d2" id="tl"></div>
  </div>`;
  const paint = () => {
    const rows = all.filter((e) => (type === "all" || e.type === type) && (!q || `${e.title} ${e.id}`.toLowerCase().includes(q)));
    let day = "", out = "";
    for (const e of rows.slice(0, 400)) {
      const d = fmt.date(e.at); if (d !== day) { day = d; out += `<div class="tl-day">${d}</div>`; }
      const href = e.experimentId ? `#experiments/${e.experimentId}` : e.conversationId ? `#research/${e.conversationId}` : null;
      const tag = href ? "a" : "div";
      out += `<${tag} class="tl-item" ${href ? `href="${href}"` : ""}><span class="li-icon">${icon(IC[e.type] || "history", 13)}</span><div class="li-main"><div class="li-title">${esc(e.title)}</div><div class="li-sub">${esc(e.type)}${e.type === "commit" ? ` · ${esc(e.id)}` : ""}${e.costUsd != null ? ` · $${(+e.costUsd).toFixed(3)}` : ""}${e.error ? ` · ${esc(e.error)}` : ""}</div></div><span class="li-right muted">${fmt.time(e.at)}</span></${tag}>`;
    }
    $("#tl", main).innerHTML = out || emptyState(icon("history"), "Nothing here", "No events match this filter.");
  };
  $("#hq", main).addEventListener("input", debounce((e) => { q = e.target.value.toLowerCase(); paint(); }, 120));
  $$(".seg button", main).forEach((b) => b.addEventListener("click", () => { type = b.dataset.t; $$(".seg button", main).forEach((x) => x.setAttribute("aria-pressed", x === b)); paint(); }));
  paint();
}
