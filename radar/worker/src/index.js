/**
 * Radar: alerts when a wallet we follow buys something.
 *
 * Helius pushes each tracked wallet's transactions here, so the delay between
 * the buy landing on chain and the message arriving is seconds rather than the
 * minute and a half that polling cost us.
 *
 * The rule is deliberately plain: one buy by one wallet on the list is the
 * alert. Waiting for several wallets to converge was what made the earlier
 * version late, and late is the same as useless here.
 */
import { extractBuys } from "./detect.js";
import { marketCap } from "./marketcap.js";
import { operators, isSprayer, oversized } from "./crazy.js";
import { recordEntry, fillDueOutcomes } from "./outcomes.js";
import { pollSlice, extractBuysRaw } from "./poll.js";
import { TRACKED, FEED } from "./wallets.js";
export { ClusterState } from "./cluster.js";

// Two audiences. TRACKED are the wallets that earned a place by their own
// results and go to the quiet channel; FEED is the wide set, where volume is
// the point and the reader goes looking rather than being interrupted.
const TRACKED_SET = new Set(Object.keys(TRACKED));
const FEED_SET = new Set(Object.keys(FEED));
const WATCHED = new Set([...TRACKED_SET, ...FEED_SET]);

function html(text) {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

/** Score for a group of wallets landing on the same mint.
 *
 * Breadth and speed only. The previous scoring mixed in size and novelty with
 * weights nobody had checked, and its top-scoring alert fell 91%; these two
 * inputs are at least directly observable. Treat the number as a label for how
 * unusual the cluster is, not as a forecast.
 */
function scoreCluster(buyers) {
  const span = (Math.max(...buyers.map((b) => b.ts)) - Math.min(...buyers.map((b) => b.ts))) / 1000;
  const breadth = Math.min(1, (buyers.length - 1) / 4);
  const speed = Math.min(1, Math.max(0, 1 - span / 600));
  // Breadth and speed alone say nothing about who is buying. A cluster that
  // includes the shortlist wallets is worth more than the same shape drawn
  // from the wide feed, so it earns a bonus on top rather than reweighting.
  const quality = Math.min(1, buyers.filter((b) => b.isSignal).length / 2);
  const base = 100 * (0.65 * breadth + 0.35 * speed);
  return { score: Math.min(100, Math.round(base + 15 * quality)), span: Math.round(span) };
}

function formatCluster(buyers, mint) {
  const { score, span } = scoreCluster(buyers);
  const sol = buyers.reduce((sum, b) => sum + b.sol, 0).toFixed(2);
  const band = score >= 75 ? "\u{1F534} STRONG" : score >= 50 ? "\u{1F7E0} NOTABLE" : "\u{1F7E1} EARLY";
  return [
    `${band}  \u00b7  ${score}/100`,
    "",
    `<b>${buyers.length} wallets you follow bought the SAME token</b>`,
    `within ${span} seconds of each other.`,
    "",
    "<b>Who bought:</b>",
    ...buyers.map((b) => `  \u2022 ${html(b.name)} — ${b.sol} SOL`),
    "",
    `<b>Total:</b> ${sol} SOL`,
    "",
    `<code>${html(mint)}</code>`,
    "",
    `\u{1F4C8} <a href="https://dexscreener.com/solana/${mint}">Chart</a>  \u00b7  ` +
      `\u{1F9FE} <a href="https://axiom.trade/t/${mint}">Axiom</a>`,
  ].join("\n");
}

function formatAlert(buy, name) {
  const mint = buy.mint;
  return [
    `🟢 <b>${html(name)}</b> just bought`,
    "",
    `<b>${buy.sol_spent} SOL</b>`,
    "",
    `<code>${html(mint)}</code>`,
    "",
    `📈 <a href="https://dexscreener.com/solana/${mint}">Chart</a>  ·  ` +
      `🧾 <a href="https://axiom.trade/t/${mint}">Axiom</a>  ·  ` +
      `🔍 <a href="https://solscan.io/token/${mint}">Solscan</a>`,
    "",
    "<i>Not a buy signal — a wallet you follow moved. Go look.</i>",
  ].join("\n");
}

/**
 * A drill must never be able to reach the phone. Labelling a test message was
 * not enough — a test that looks like an alert IS an alert to whoever reads
 * it — so a drill now renders the message back to its caller and stops there.
 */
async function sendTelegram(env, text, channel = "signal", drill = false) {
  if (drill) {
    (drill.rendered ||= []).push({ channel, text });
    return true;
  }
  const tokens = {
    feed: env.TELEGRAM_FEED_TOKEN,
    legends: env.TELEGRAM_LEGENDS_TOKEN,
    signal: env.TELEGRAM_BOT_TOKEN,
  };
  const chats = {
    feed: env.TELEGRAM_FEED_CHAT,
    legends: env.TELEGRAM_LEGENDS_CHAT,
    signal: env.TELEGRAM_CHAT_ID,
  };
  const token = tokens[channel];
  const chat = chats[channel];
  if (!token || !chat) return false;
  const resp = await fetch(
    `https://api.telegram.org/bot${token}/sendMessage`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        chat_id: chat,
        text,
        parse_mode: "HTML",
        disable_web_page_preview: true,
      }),
    },
  );
  return resp.ok;
}

async function recordBuy(env, buy, name, isSignal) {
  await env.DB.prepare(
    "INSERT OR IGNORE INTO buys (mint, wallet, name, sol, ts, is_signal) VALUES (?, ?, ?, ?, ?, ?)",
  ).bind(buy.mint, buy.wallet, name, buy.sol_spent, Date.now(), isSignal ? 1 : 0).run();
}

async function buyersOf(env, mint, windowMs) {
  const { results } = await env.DB.prepare(
    "SELECT wallet, name, sol, ts, is_signal FROM buys WHERE mint = ? AND ts >= ? ORDER BY ts",
  ).bind(mint, Date.now() - windowMs).all();
  return (results || []).map((r) => ({
    wallet: r.wallet, name: r.name, sol: r.sol, ts: r.ts, isSignal: r.is_signal === 1,
  }));
}

async function logAlert(env, kind, mint, wallets, score, payload) {
  await env.DB.prepare(
    "INSERT INTO alerts (kind, mint, wallets, score, ts, payload) VALUES (?, ?, ?, ?, ?, ?)",
  ).bind(kind, mint, wallets, score, Date.now(), JSON.stringify(payload)).run();
}

/**
 * Providers disagree on shape. One sends an array of enriched transactions
 * with transfers already broken out; the block-filter template sends
 * { block, transactions: [{ raw }] } holding plain RPC transactions. Normalise
 * here so the rest of the worker does not care which is connected.
 */
function normalisePayload(payload) {
  // The block-filter template sends blocks, and may send one or a batch of
  // them; each block carries plain RPC transactions under `raw`. The enriched
  // format, by contrast, is a flat array of transactions.
  const items = Array.isArray(payload) ? payload : [payload];
  const blocks = items.filter((i) => i && Array.isArray(i.transactions));
  if (blocks.length) {
    const txs = [];
    for (const b of blocks) {
      const blockTime = b.block?.blockTime ?? b.blockTime;
      for (const entry of b.transactions) {
        const tx = entry?.raw || entry;
        if (!tx) continue;
        txs.push(!tx.blockTime && blockTime ? { ...tx, blockTime } : tx);
      }
    }
    return { raw: true, txs };
  }
  return { raw: false, txs: items };
}

/** Which wallets we follow appear in this transaction. */
function watchedOwners(tx) {
  const keys = tx?.transaction?.message?.accountKeys || [];
  const owners = [];
  for (const k of keys) {
    const pubkey = typeof k === "string" ? k : k?.pubkey;
    if (pubkey && WATCHED.has(pubkey)) owners.push(pubkey);
  }
  return owners;
}

async function handleWebhook(request, env, ctx) {
  // The webhook URL is effectively the credential, so it carries a secret.
  const url = new URL(request.url);
  if (!env.HOOK_SECRET || url.searchParams.get("s") !== env.HOOK_SECRET) {
    return new Response("forbidden", { status: 403 });
  }

  const drill = url.searchParams.get("drill") === "1" ? { rendered: [] } : false;
  let payload;
  try {
    payload = await request.json();
  } catch {
    return new Response("bad json", { status: 400 });
  }
  const { raw: isRaw, txs: transactions } = normalisePayload(payload);

  const minSol = Number(env.MIN_SOL_BUY || "0.05");
  let alerted = 0;

  for (const tx of transactions) {
    const buys = isRaw
      ? watchedOwners(tx).flatMap((owner) => extractBuysRaw(tx, owner, minSol))
      : extractBuys(tx, WATCHED, minSol);
    for (const buy of buys) {
      alerted += await handleBuy(env, buy, { drill, ctx });
    }
  }

  return Response.json({
    ok: true,
    transactions: transactions.length,
    alerted,
    ...(drill ? { drill: true, sent_to_telegram: 0, would_send: drill.rendered } : {}),
  });
}

async function listAlerts(env) {
  const { results } = await env.DB.prepare(
    "SELECT kind, mint, wallets, score, ts, payload FROM alerts ORDER BY ts DESC LIMIT 100",
  ).all();
  return Response.json({ count: (results || []).length, alerts: results || [] });
}

// Cluster detection in memory. Storage is the durable record, but its daily
// limits can stop it, and a cluster window is only minutes wide — short enough
// that the worker's own memory covers most of it at no quota cost.
const recentBuys = new Map(); // mint -> [{wallet,name,sol,ts,isSignal}]
const firedClusters = new Map(); // `${mint}:${count}` -> ts
// Identifies which instance answered. Clusters only merge inside one instance
// when storage is down, so this is what tells that story from outside.
const ISOLATE = Math.random().toString(36).slice(2, 8);

function rememberBuy(buy, name, isSignal, windowMs) {
  const now = Date.now();
  for (const [mint, rows] of recentBuys) {
    const live = rows.filter((r) => now - r.ts < windowMs);
    if (live.length) recentBuys.set(mint, live);
    else recentBuys.delete(mint);
  }
  for (const [key, ts] of firedClusters) {
    if (now - ts > windowMs * 3) firedClusters.delete(key);
  }
  const rows = recentBuys.get(buy.mint) || [];
  if (!rows.some((r) => r.wallet === buy.wallet)) {
    rows.push({ wallet: buy.wallet, name, sol: buy.sol_spent, ts: now, isSignal });
    recentBuys.set(buy.mint, rows);
  }
  return rows;
}

function claimOnce(key) {
  if (firedClusters.has(key)) return false;
  firedClusters.set(key, Date.now());
  return true;
}

/**
 * Legends fires a handful of times a week, and the whole point is not to miss
 * one. So it is not sent once and left to sit in a list of notifications: the
 * alert goes out immediately, then keeps knocking.
 *
 * Telegram throttles a chat at roughly a message a second, so the repeats are
 * spaced and sent after the response has already gone back — the first message
 * must not wait behind the other fourteen.
 *
 * Each repeat says something different. Fifteen copies of one message is a
 * wall the eye slides off; fifteen different ones each have to be read, and
 * every one carries the mint, so whichever gets noticed is the one that works.
 */
const NAG_LINES = [
  "\u{1F6A8} <b>Legends 101</b> — this is the rare one. Go look.",
  "\u{23F0} Still waiting on you. Legends fires a few times a WEEK.",
  "\u{1F440} You have not opened it yet. This is the one you asked not to miss.",
  "\u{1F4B0} Your best wallets are already in. The clock is the whole edge here.",
  "\u26A1 Every minute here is the difference between early and late.",
  "\u{1F514} Legends 101. Not the feed. Not a cluster. The rare one.",
  "\u{1F3AF} This passed every gate: score, your best wallets, size, market cap.",
  "\u{1F6A8} Second reminder. Same token. Still small.",
  "\u{1F4C8} If you are going to look at one alert today, it is this one.",
  "\u23F3 Late is the same as useless here. That was the whole point.",
  "\u{1F525} Legends 101 \u2014 last few reminders.",
  "\u{1F6A8} Final calls. Open it or let it go on purpose, not by accident.",
  "\u{1F4CD} Still here. Still the rare one.",
  "\u{1F3C6} Legends 101. That is all.",
];

async function blastLegend(env, text, mint, opts) {
  const count = Math.max(1, Number(env.LEGENDS_BLAST_COUNT || "12"));
  const gapMs = Number(env.LEGENDS_BLAST_GAP_MS || "1200");

  // The alert itself, now — nothing waits behind the reminders.
  const first = await sendTelegram(env, text, "legends", opts.drill);

  const link = `\u{1F4C8} <a href="https://dexscreener.com/solana/${mint}">Chart</a>  \u00b7  ` +
    `\u{1F9FE} <a href="https://axiom.trade/t/${mint}">Axiom</a>`;
  const nag = async () => {
    for (let i = 0; i < count - 1; i += 1) {
      await new Promise((r) => setTimeout(r, gapMs));
      const line = NAG_LINES[i % NAG_LINES.length];
      await sendTelegram(env,
        `${line}\n\n<code>${html(mint)}</code>\n\n${link}`, "legends", opts.drill);
    }
  };
  // waitUntil keeps the reminders running after the response is returned, so
  // the alert is never held up by them. A drill waits instead: reminders that
  // finish after the response are reminders a drill cannot check.
  if (opts.ctx && !opts.drill) opts.ctx.waitUntil(nag());
  else await nag();
  return first;
}

/**
 * Legends 101.
 *
 * A separate, deliberately rare channel. It cannot tell you a coin will reach
 * five million — nothing on chain can, because market cap is about what a
 * token IS and a wallet feed only says who is buying. What it can say is that
 * the wallets with the best records are buying the same thing, at size, at
 * once, while it is still small enough for five million to be a real move.
 *
 * Every bar here is deliberately extreme. A channel that fires daily is the
 * feed channel again under a different name.
 */
// A drill gets its own state so fake buys never join a real roster.
function clusterStub(env, opts) {
  return env.CLUSTERS.get(env.CLUSTERS.idFromName(opts.drill ? "drill" : "global"));
}

/**
 * Per-wallet habits, so "unusual" can be measured against the wallet's own
 * normal rather than a number picked out of the air. Refreshed rarely and
 * cached, since this only gates a channel that fires a few times a day, and
 * a stale habit is far better than no habit at all.
 */
let habits = { at: 0, counts: new Map(), medians: new Map() };

async function walletHabits(env) {
  if (Date.now() - habits.at < 15 * 60_000 && habits.counts.size) return habits;
  const since = Date.now() - 48 * 3600 * 1000;
  const { results } = await env.DB.prepare(
    "SELECT name, COUNT(*) n, AVG(sol) avg_sol FROM buys WHERE ts > ? GROUP BY name",
  ).bind(since).all();
  const counts = new Map();
  const medians = new Map();
  for (const r of results || []) {
    const key = r.name.toLowerCase().replace(/[^a-z0-9]/g, "") || r.name;
    counts.set(key, (counts.get(key) || 0) + r.n);
    medians.set(r.name, r.avg_sol);
  }
  habits = { at: Date.now(), counts, medians };
  return habits;
}

async function legendsVerdict(env, buyers, mint, opts = {}) {
  // Kill switch. This channel told its reader to buy two tokens that lost
  // them money, so it stays off until it can tell a rug from a runner.
  // A drill still evaluates: it reports back to whoever ran it and reaches
  // no one, and a channel that cannot be exercised cannot be fixed.
  if (!opts.drill && String(env.LEGENDS_ENABLED || "true") !== "true") {
    return { pass: false, why: "channel disabled" };
  }
  const minOps = Number(env.LEGENDS_MIN_OPERATORS || "8");
  const minSol = Number(env.LEGENDS_MIN_SOL || "25");
  const sprayLimit = Number(env.LEGENDS_SPRAYER_BUYS || "200");
  const minLiquidity = Number(env.LEGENDS_MIN_LIQUIDITY || "5000");
  const bigMultiple = Number(env.LEGENDS_OVERSIZED_MULTIPLE || "3");

  // Habits are a refinement; without them the core bars still hold.
  let counts = new Map();
  let medians = new Map();
  try {
    ({ counts, medians } = await walletHabits(env));
  } catch (err) {
    console.log(`habits unavailable (${err.message}); gating without them`);
  }

  const serious = counts.size
    ? buyers.filter((b) => !isSprayer(b.name, counts, sprayLimit))
    : buyers;
  const people = operators(serious);
  const sol = serious.reduce((sum, b) => sum + b.sol, 0);

  if (people.size < minOps) {
    return { pass: false, why: `${people.size} people < ${minOps}` };
  }
  if (sol < minSol) return { pass: false, why: `${sol.toFixed(1)} SOL < ${minSol}` };

  // The cap this used to have excluded the best thing it ever saw, because
  // "crazy" is not the same as "tiny". What has to be checked instead is that
  // the token can be sold at all: a rug reads as small and cheap right up
  // until the liquidity is gone.
  const { mc, known, notIndexed, liquidity, ageMinutes, reason } = await marketCap(mint);
  if (!known && !notIndexed) {
    return { pass: false, why: `cannot price it (${reason})` };
  }
  if (liquidity != null && liquidity < minLiquidity) {
    return { pass: false, why: `liquidity $${Math.round(liquidity)} under floor` };
  }
  if (notIndexed || liquidity == null) {
    return { pass: false, why: "no tradeable market found yet" };
  }

  const span = (Math.max(...serious.map((b) => b.ts))
    - Math.min(...serious.map((b) => b.ts))) / 1000;
  return {
    pass: true,
    people: people.size,
    sol,
    span: Math.round(span),
    oversized: medians.size ? oversized(serious, medians, bigMultiple) : 0,
    buyers: serious,
    mc, liquidity, ageMinutes,
  };
}

function formatLegend(buyers, mint, v) {
  const rows = v.buyers || buyers;
  return [
    "\u{1F3C6} <b>LEGENDS 101</b>",
    "",
    `<b>${v.people} different people</b> bought this within ` +
      `${v.span < 60 ? `${v.span}s` : `${Math.round(v.span / 60)}m`} \u2014 ` +
      `${v.sol.toFixed(1)} SOL total.`,
    v.oversized ? `<b>${v.oversized}</b> of them bought far bigger than they normally do.` : "",
    "",
    "<b>Who bought:</b>",
    ...rows.map((b) => `  ${b.isSignal ? "\u2b50" : "  "} ${html(b.name)} \u2014 ${b.sol} SOL`),
    "",
    v.mc ? `<b>Market cap:</b> $${Math.round(v.mc).toLocaleString()}` : "",
    v.liquidity ? `<b>Liquidity:</b> $${Math.round(v.liquidity).toLocaleString()}` : "",
    v.ageMinutes != null ? `<b>Age:</b> ${v.ageMinutes} min` : "",
    "",
    "<i>This says a lot of people moved at once. It does not say the token "
      + "goes up, and it cannot tell you the liquidity will still be there.</i>",
    "",
    `<code>${html(mint)}</code>`,
    "",
    `\u{1F4C8} <a href="https://dexscreener.com/solana/${mint}">Chart</a>  \u00b7  ` +
      `\u{1F9FE} <a href="https://axiom.trade/t/${mint}">Axiom</a>`,
  ].filter((line) => line !== "").join("\n");
}

/**
 * Legends says each token once. A cluster that keeps growing re-announces
 * itself on the other channels by design; here it would just be the same
 * call, louder, and a channel that repeats itself is not rare.
 */
async function claimLegend(env, mint, opts) {
  try {
    const resp = await clusterStub(env, opts).fetch("https://clusters/claim", {
      method: "POST", body: JSON.stringify({ claimKey: `legend:${mint}` }),
    });
    return (await resp.json()).granted;
  } catch {
    return claimOnce(`legend:${mint}`);
  }
}

/** Shared by the pushed and polled paths so both alert identically. */
async function handleBuy(env, buy, opts = {}) {
  // Master switch. Nothing is sent, stored or looked up while this is off.
  if (!opts.drill && String(env.RADAR_ENABLED || "true") !== "true") return 0;
  const isSignal = TRACKED_SET.has(buy.wallet);
  const name = TRACKED[buy.wallet] || FEED[buy.wallet] || buy.wallet.slice(0, 6);
  const windowMs = Number(env.CLUSTER_WINDOW_MINUTES || "10") * 60_000;
  const minCluster = Number(env.MIN_FEED_WALLETS || "2");
  const minScore = Number(env.MIN_FEED_SCORE || "80");
  let sent = 0;

  // The cluster object holds the one true roster. Its own memory is the
  // fallback: worse, because buys scatter across instances, but it keeps the
  // radar alerting rather than silent if the object cannot be reached.
  let buyers = null;
  let singleClaim = false;
  let clusterClaim = false;
  try {
    const stub = clusterStub(env, opts);
    const resp = await stub.fetch("https://clusters/buy", {
      method: "POST",
      body: JSON.stringify({
        mint: buy.mint, wallet: buy.wallet, name, sol: buy.sol_spent,
        isSignal, windowMs, minCluster,
      }),
    });
    ({ buyers, singleClaim, clusterClaim } = await resp.json());
  } catch (err) {
    console.log(`cluster state unavailable (${err.message}); falling back to memory`);
    buyers = rememberBuy(buy, name, isSignal, windowMs);
    singleClaim = isSignal && claimOnce(`single:${buy.wallet}:${buy.mint}`);
    clusterClaim = buyers.length >= minCluster
      && claimOnce(`cluster:${buy.mint}:${buyers.length}`);
  }

  // `sent` counts messages that actually reached a phone, not rules that
  // matched: a claimed cluster scoring under the bar sends nothing, and
  // reporting it as an alert is how silence gets mistaken for delivery.
  const deliver = async (text, channel) => {
    const ok = await sendTelegram(env, text, channel, opts.drill);
    if (ok) sent += 1;
    else console.log(`telegram ${channel} send failed for ${buy.mint}`);
  };

  if (singleClaim) await deliver(formatAlert(buy, name), "signal");

  const { score } = scoreCluster(buyers);
  if (clusterClaim) {
    const text = formatCluster(buyers, buy.mint);
    if (score >= minScore) {
      await deliver(text, "feed");
      // The shape of the cluster is only knowable now; the price is only
      // knowable now. Both are needed to ever say whether this was worth
      // sending, so they are written down before the moment passes — but
      // never for a drill, whose invented buys would be learned from as
      // though they had happened.
      const counts = (await walletHabits(env).catch(() => null))?.counts || new Map();
      const span = (Math.max(...buyers.map((b) => b.ts))
        - Math.min(...buyers.map((b) => b.ts))) / 1000;
      const shape = {
        people: operators(buyers).size,
        wallets: buyers.length,
        sol: buyers.reduce((sum, b) => sum + b.sol, 0),
        maxSol: Math.max(...buyers.map((b) => b.sol)),
        span: Math.round(span),
        selective: counts.size
          ? buyers.filter((b) => !isSprayer(b.name, counts, 60)).length : null,
      };
      if (!opts.drill) {
        const write = recordEntry(env, buy.mint, shape, score).catch(
          (err) => console.log(`outcome entry failed: ${err.message}`));
        if (opts.ctx) opts.ctx.waitUntil(write); else await write;
      }
    }
    else console.log(`cluster ${buy.mint} n=${buyers.length} score=${score} below ${minScore}`);
    if (buyers.some((b) => b.isSignal)) await deliver(text, "signal");

    const verdict = await legendsVerdict(env, buyers, buy.mint, opts);
    if (!verdict.pass) {
      console.log(`legends skip ${buy.mint}: ${verdict.why}`);
    } else if (await claimLegend(env, buy.mint, opts)) {
      const legendText = formatLegend(buyers, buy.mint, verdict);
      if (await blastLegend(env, legendText, buy.mint, opts)) sent += 1;
      else console.log(`telegram legends send failed for ${buy.mint}`);
    }
  }

  // The database is the durable record for later calibration, nothing more:
  // alerting no longer depends on it, so its limits cannot silence the radar.
  // A drill leaves no trace in it; invented buys must not reach the record
  // the thresholds are later calibrated against.
  if (opts.drill) return sent;
  try {
    await recordBuy(env, buy, name, isSignal);
    if (sent) {
      await logAlert(env, clusterClaim ? "cluster" : "single",
                     buy.mint, buyers.length, score, { wallet: name });
    }
  } catch (err) {
    console.log(`storage unavailable (${err.message}); alert already sent`);
  }
  return sent;
}

export default {
  /**
   * Scheduled scan. This is the path that keeps the radar alive when the
   * pushed feed has no quota left; it covers the selected wallets only.
   */
  async scheduled(event, env, ctx) {
    const minSol = Number(env.MIN_SOL_BUY || "0.05");
    const wallets = Object.keys(TRACKED);
    const slices = Number(env.POLL_SLICES || "2");
    const slice = Math.floor(Date.now() / 60_000) % slices;
    const result = await pollSlice(env, wallets, slice, slices, minSol, async (buy) => {
      await handleBuy(env, buy);
    });
    // Outcomes are filled a few at a time, behind the scan, so learning what
    // an alert was worth never competes with sending one.
    ctx.waitUntil(fillDueOutcomes(env).catch(
      (err) => console.log(`outcome fill failed: ${err.message}`)));

    // Heartbeat: without it, a quiet scan and a scan that never ran look the
    // same from outside.
    await env.DB.prepare(
      "INSERT OR REPLACE INTO sent (key, ts) VALUES ('heartbeat', ?)",
    ).bind(Date.now()).run();
    console.log(`poll slice ${slice}/${slices}: scanned ${result.scanned}, buys ${result.found}`);
  },

  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname === "/hook" && request.method === "POST") {
      return handleWebhook(request, env, ctx);
    }
    if (url.pathname === "/alerts") return listAlerts(env);
    if (url.pathname === "/rpctest") {
      const eps = [
        "https://solana-rpc.publicnode.com",
        "https://solana.drpc.org",
        "https://endpoints.omniatech.io/v1/sol/mainnet/public",
        "https://solana.api.onfinality.io/public",
      ];
      const w = Object.keys(TRACKED)[2];
      const out = [];
      for (const ep of eps) {
        try {
          const r = await fetch(ep, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "getSignaturesForAddress", params: [w, { limit: 2 }] }),
          });
          const body = await r.text();
          out.push({ ep, status: r.status, ok: r.status === 200 && !body.includes("error"), body: body.slice(0, 110) });
        } catch (err) {
          out.push({ ep, error: err.message });
        }
      }
      return Response.json(out);
    }
    if (url.pathname === "/parse" && request.method === "POST") {
      // Returns what the extractor saw, so a miss can be explained instead of
      // guessed at.
      const body = await request.json();
      const { raw, txs } = normalisePayload(body);
      const minSol = Number(env.MIN_SOL_BUY || "0.05");
      const report = txs.map((tx) => {
        const keys = (tx?.transaction?.message?.accountKeys || []).map((k) =>
          typeof k === "string" ? k : k?.pubkey);
        const owners = keys.filter((k) => WATCHED.has(k));
        return {
          version: tx?.version,
          keys: keys.length,
          owners,
          err: tx?.meta?.err ? String(tx.meta.err).slice(0, 60) : null,
          preBalances: (tx?.meta?.preBalances || []).length,
          postTokenBalances: (tx?.meta?.postTokenBalances || []).length,
          buys: owners.flatMap((o) => extractBuysRaw(tx, o, minSol)),
        };
      });
      return Response.json({ raw, txs: txs.length, report });
    }
    if (url.pathname === "/poll") {
      // Same work the schedule does, reachable by hand so a failure is visible.
      try {
        const minSol = Number(env.MIN_SOL_BUY || "0.05");
        const wallets = Object.keys(TRACKED);
        const slices = Number(url.searchParams.get("slices") || env.POLL_SLICES || "2");
        const slice = Number(url.searchParams.get("slice") || Math.floor(Date.now() / 60_000) % slices);
        let sent = 0;
        const result = await pollSlice(env, wallets, slice, slices, minSol, async (buy) => {
          sent += await handleBuy(env, buy);
        });
        return Response.json({ ok: true, slice, slices, ...result, alerts: sent });
      } catch (err) {
        return Response.json({ ok: false, error: err.message, stack: String(err.stack).slice(0, 300) }, { status: 500 });
      }
    }
    if (url.pathname === "/test") {
      const ok = await sendTelegram(env, "🟢 <b>Radar is live.</b>\nThis is a connection test.");
      const feedOk = await sendTelegram(
        env, "\u{1F4E1} <b>Radar feed is live.</b>\nThis is a connection test.", "feed");
      const legendsOk = await sendTelegram(
        env, "\u{1F3C6} <b>Legends 101 is live.</b>\nThis is a connection test.", "legends");
      return Response.json({ signal: ok, feed: feedOk, legends: legendsOk });
    }
    let counts = null;
    try {
      counts = await env.DB.prepare(
        "SELECT COUNT(*) AS buys FROM buys WHERE ts > ?",
      ).bind(Date.now() - 24 * 3600 * 1000).first();
    } catch (err) {
      return Response.json({ status: "degraded", storage: err.message.slice(0, 120),
                             isolate: ISOLATE, mints_in_memory: recentBuys.size,
                             tracking: TRACKED_SET.size, feed: FEED_SET.size });
    }
    let hb = null;
    try {
      hb = await env.DB.prepare("SELECT ts FROM sent WHERE key = 'heartbeat'").first();
    } catch {}
    return Response.json({
      status: "ok",
      tracking: TRACKED_SET.size,
      feed: FEED_SET.size,
      isolate: ISOLATE,
      mints_in_memory: recentBuys.size,
      last_scan_seconds_ago: hb ? Math.round((Date.now() - hb.ts) / 1000) : null,
      buys_24h: counts?.buys ?? 0,
    });
  },
};
