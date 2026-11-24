// Graveyard: every rejected strategy and rejected experiment, with the reason and the numbers that killed it.
import { api } from "../api.js";
import { $, esc, fmt, signCls, skeleton, emptyState, debounce } from "../util.js";
import { icon } from "../icons.js";

export default async function graveyard(main) {
  main.innerHTML = skeleton([60, 400]);
  const [strats, exps] = await Promise.all([api.strategies(), api.experiments()]);
  const dead = strats.filter((s) => s.status === "DEAD"), rej = exps.filter((x) => x.status === "rejected");
  main.innerHTML = `
  <div class="page wide">
    <div class="page-head fade-in"><div><h1>Graveyard</h1><p>${dead.length} strategies and ${rej.length} experiments were tested, priced, compared to random, and buried.</p></div>
      <div class="actions"><div class="search" style="width:260px"><label class="sr-only" for="gq">Search the graveyard</label>${icon("search", 14)}<input id="gq" class="input" placeholder="Search…"></div></div></div>
    <div class="grave-grid fade-in d1" id="gg"></div>
  </div>`;
  const paint = (q = "") => {
    const card = (s) => `<a class="grave" href="#strategies/${s.id}"><h4>${esc(s.name)} <span class="pill dead">dead</span></h4><p>${esc(s.rule)}</p><div class="reason">${esc(s.note)}</div>
      <div class="foot"><span>${esc(s.market)}</span><span>${esc(s.family)}</span>${s.hasTrades ? `<span class="${signCls(s.oosAvg)}">2020–26 ${fmt.rr(s.oosAvg, 3)}</span><span>${fmt.n(s.n)} trades</span>` : ""}<span>p ${esc(s.pRandom ?? "—")}</span></div></a>`;
    const ecard = (x) => `<a class="grave" href="#experiments/${x.id}"><h4>${esc(x.name)} <span class="pill rejected">rejected</span></h4><p>${esc(x.hypothesis || "")}</p><div class="reason">${esc(x.notes || x.history.at(-1)?.note || "Rejected after review")}</div>
      <div class="foot"><span>experiment</span>${x.baseName ? `<span>from ${esc(x.baseName)}</span>` : ""}${x.result?.metrics?.oos_avg_r != null ? `<span>2020–26 ${fmt.rr(x.result.metrics.oos_avg_r, 3)}</span>` : ""}<span>${fmt.date(x.history.at(-1)?.at)}</span></div></a>`;
    const m = (t) => !q || t.toLowerCase().includes(q);
    const html = [...dead.filter((s) => m(`${s.name} ${s.rule} ${s.note} ${s.family}`)).map(card), ...rej.filter((x) => m(`${x.name} ${x.hypothesis} ${x.notes}`)).map(ecard)].join("");
    $("#gg", main).innerHTML = html || emptyState(icon("grave"), "Nothing matches", "Try another word.");
  };
  $("#gq", main).addEventListener("input", debounce((e) => paint(e.target.value.toLowerCase()), 120));
  paint();
}
