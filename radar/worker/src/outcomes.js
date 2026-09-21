/**
 * What happened next.
 *
 * Every question worth asking about this radar is about outcomes, and none
 * of them could be answered. Whether the score meant anything, whether a
 * faster alert would have helped, whether entering every alert wins or
 * loses — all of it needs the price at the moment of the alert, and that was
 * never written down. Survival could be checked afterwards, because a dead
 * token stays dead; return could not, because the entry was gone.
 *
 * So each alert now records the market as it stood, along with the shape of
 * the cluster that caused it, and the same token is priced again later. The
 * answers are three days away rather than available now, which is the cost
 * of not having done this at the start.
 */
import { marketCap } from "./marketcap.js";

/** Records an alert's starting point. Failure here costs data, never an alert. */
export async function recordEntry(env, mint, cluster, score) {
  const { price, mc, liquidity } = await marketCap(mint);
  await env.DB.prepare(
    `INSERT OR IGNORE INTO outcomes
       (mint, alert_ts, people, wallets, sol, max_sol, span_s, selective, score,
        entry_price, entry_mc, entry_liq)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
  ).bind(mint, Date.now(), cluster.people, cluster.wallets, cluster.sol,
    cluster.maxSol, cluster.span, cluster.selective, score,
    price, mc, liquidity).run();
}

const HORIZONS = [
  { column: "p5m", mcCol: "mc5m", liqCol: "liq5m", afterMs: 5 * 60_000 },
  { column: "p1h", mcCol: "mc1h", liqCol: "liq1h", afterMs: 60 * 60_000 },
  { column: "p24h", mcCol: "mc24h", liqCol: "liq24h", afterMs: 24 * 3600_000 },
];

/**
 * Fills in whichever horizons have come due. Called from the scheduled scan,
 * a few at a time, so it never competes with the alert path.
 */
export async function fillDueOutcomes(env, limit = 5) {
  let filled = 0;
  for (const h of HORIZONS) {
    const { results } = await env.DB.prepare(
      `SELECT mint FROM outcomes
        WHERE ${h.column} IS NULL AND alert_ts <= ?
        ORDER BY alert_ts LIMIT ?`,
    ).bind(Date.now() - h.afterMs, limit).all();

    for (const row of results || []) {
      const { price, mc, liquidity, known, notIndexed } = await marketCap(row.mint);
      // A token nobody lists any more is worth nothing, and that is the
      // outcome, not a missing reading. A failed lookup is neither, so it
      // waits for the next pass.
      if (!known && !notIndexed) continue;
      await env.DB.prepare(
        `UPDATE outcomes SET ${h.column} = ?, ${h.mcCol} = ?, ${h.liqCol} = ?
          WHERE mint = ?`,
      ).bind(notIndexed ? 0 : price, notIndexed ? 0 : mc,
        notIndexed ? 0 : liquidity, row.mint).run();
      filled += 1;
    }
  }
  return filled;
}
