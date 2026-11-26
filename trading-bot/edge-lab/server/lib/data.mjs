// Research data layer: reads the Edge Lab registry (research/lab/data.json) and the per-trade series
// (research/lab/trades.json), and derives every metric the app shows from the actual trades.
import fs from "node:fs";
import path from "node:path";
import { enrich } from "./enrich.mjs";
export { summary } from "./enrich.mjs";

export class ResearchData {
  constructor(labDir) {
    this.labDir = labDir;
    this.files = { registry: path.join(labDir, "data.json"), trades: path.join(labDir, "trades.json") };
    this.cache = null; this.stamp = "";
  }

  /** Reload when either file changed on disk (the research agent or build.py may rewrite them). */
  load() {
    const st = Object.values(this.files).map((f) => (fs.existsSync(f) ? fs.statSync(f).mtimeMs : 0)).join("|");
    if (this.cache && st === this.stamp) return this.cache;
    if (!fs.existsSync(this.files.registry)) throw new Error(`Registry not found: ${this.files.registry}. Run python3 build.py in research/lab.`);
    const reg = JSON.parse(fs.readFileSync(this.files.registry, "utf8"));
    const trades = fs.existsSync(this.files.trades) ? JSON.parse(fs.readFileSync(this.files.trades, "utf8")) : {};
    const strategies = reg.strategies.map((s) => enrich(s, trades[s.id] || (s.series && trades[s.series])));
    this.cache = { meta: { updated: reg.updated, theoriesTested: reg.theories_tested, book: reg.book, files: this.fileInfo() }, strategies, sp: reg.sp || null, trades };
    this.stamp = st;
    return this.cache;
  }

  fileInfo() {
    return Object.entries(this.files).map(([k, f]) => ({ key: k, path: f, exists: fs.existsSync(f), modified: fs.existsSync(f) ? fs.statSync(f).mtime.toISOString() : null }));
  }

  /** Raw trade returns for one strategy (null when the strategy has no trade series). */
  series(id) {
    const d = this.load(); const s = d.strategies.find((x) => x.id === id);
    if (!s) return null;
    const tr = d.trades[id] || (s.series && d.trades[s.series]);
    return tr ? { t: tr.t, r: tr.r, units: tr.units } : null;
  }
}
