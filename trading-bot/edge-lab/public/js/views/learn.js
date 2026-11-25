// Learn: quant trading lessons in Hebrew, with live numbers from the lab and small calculators.
import { api } from "../api.js";
import { skeleton } from "../util.js";
import { state } from "../state.js";
import { mountLearn, normalise } from "../learn/content.js";

export default async function learn(main, [start]) {
  main.innerHTML = skeleton([60, 480]);
  const rows = await api.strategies();
  main.innerHTML = `<div class="page wide"><div class="page-head fade-in"><div><h1>Learn</h1><p>The math behind every number in Edge Lab, with examples from your own strategies.</p></div></div><div id="learn-root" class="fade-in d1"></div></div>`;
  const ctl = mountLearn(main.querySelector("#learn-root"), normalise(rows), { start });
  state.context = "Learn section: quant trading lessons (expectancy, Kelly, t-stat, multiple testing, placebo, out-of-sample, Monte Carlo, streaks, Sharpe).";
  return () => ctl;
}
