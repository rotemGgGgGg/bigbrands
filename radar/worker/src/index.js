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
import { pollSlice } from "./poll.js";
import { TRACKED, FEED } from "./wallets.js";

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
  return { score: Math.round(100 * (0.65 * breadth + 0.35 * speed)), span: Math.round(span) };
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

async function sendTelegram(env, text, channel = "signal", drill = false) {
  if (drill) text = "\u{1F9EA} <b>TEST — not a real event</b>\n\n" + text;
  const token = channel === "feed" ? env.TELEGRAM_FEED_TOKEN : env.TELEGRAM_BOT_TOKEN;
  const chat = channel === "feed" ? env.TELEGRAM_FEED_CHAT : env.TELEGRAM_CHAT_ID;
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

/** Claim a message so the same one is never sent twice. */
async function claim(env, key) {
  const res = await env.DB.prepare(
    "INSERT OR IGNORE INTO sent (key, ts) VALUES (?, ?)",
  ).bind(key, Date.now()).run();
  return (res.meta?.changes ?? 0) > 0;
}

async function logAlert(env, kind, mint, wallets, score, payload) {
  await env.DB.prepare(
    "INSERT INTO alerts (kind, mint, wallets, score, ts, payload) VALUES (?, ?, ?, ?, ?, ?)",
  ).bind(kind, mint, wallets, score, Date.now(), JSON.stringify(payload)).run();
}

async function handleWebhook(request, env) {
  // The webhook URL is effectively the credential, so it carries a secret.
  const url = new URL(request.url);
  if (!env.HOOK_SECRET || url.searchParams.get("s") !== env.HOOK_SECRET) {
    return new Response("forbidden", { status: 403 });
  }

  const isDrill = url.searchParams.get("drill") === "1";
  let payload;
  try {
    payload = await request.json();
  } catch {
    return new Response("bad json", { status: 400 });
  }
  const transactions = Array.isArray(payload) ? payload : [payload];

  // Keep a counter and one sample so "nothing is arriving" can be told apart
  // from "arriving in a shape we do not parse".
  try {
    await env.DB.prepare(
      "INSERT INTO sent (key, ts) VALUES ('deliveries:' || ?, ?) ON CONFLICT(key) DO NOTHING",
    ).bind(String(Date.now()), Date.now()).run();
    await env.DB.prepare(
      "INSERT OR REPLACE INTO sent (key, ts) VALUES ('last_payload', ?)",
    ).bind(Date.now()).run();
    await env.DB.prepare(
      "INSERT OR REPLACE INTO alerts (id, kind, mint, wallets, score, ts, payload) " +
      "VALUES ((SELECT id FROM alerts WHERE kind='sample' LIMIT 1), 'sample', 'sample', 0, 0, ?, ?)",
    ).bind(Date.now(), JSON.stringify(transactions[0] || {}).slice(0, 4000)).run();
  } catch (err) {
    console.log(`diag write failed: ${err.message}`);
  }

  const minSol = Number(env.MIN_SOL_BUY || "0.05");
  let alerted = 0;

  for (const tx of transactions) {
    for (const buy of extractBuys(tx, WATCHED, minSol)) {
      alerted += await handleBuy(env, buy, { drill: isDrill });
    }
  }

  return Response.json({ ok: true, transactions: transactions.length, alerted });
}

async function listAlerts(env) {
  const { results } = await env.DB.prepare(
    "SELECT kind, mint, wallets, score, ts, payload FROM alerts ORDER BY ts DESC LIMIT 100",
  ).all();
  return Response.json({ count: (results || []).length, alerts: results || [] });
}

/** Shared by the pushed and polled paths so both alert identically. */
async function handleBuy(env, buy, opts = {}) {
  const isSignal = TRACKED_SET.has(buy.wallet);
  const name = TRACKED[buy.wallet] || FEED[buy.wallet] || buy.wallet.slice(0, 6);
  const windowMs = Number(env.CLUSTER_WINDOW_MINUTES || "10") * 60_000;
  const minCluster = Number(env.MIN_FEED_WALLETS || "2");
  let sent = 0;

  await recordBuy(env, buy, name, isSignal);

  if (isSignal && (await claim(env, `buy:${buy.wallet}:${buy.mint}`))) {
    await sendTelegram(env, formatAlert(buy, name), "signal", opts.drill);
    await logAlert(env, "single", buy.mint, 1, null, { wallet: name, sol: buy.sol_spent });
    sent += 1;
  }

  const buyers = await buyersOf(env, buy.mint, windowMs);
  if (buyers.length >= minCluster && (await claim(env, `cluster:${buy.mint}:${buyers.length}`))) {
    const text = formatCluster(buyers, buy.mint);
    // The wide feed is for the strong clusters only; everything below the bar
    // is still recorded, just not sent.
    const minScore = Number(env.MIN_FEED_SCORE || "80");
    if (scoreCluster(buyers).score >= minScore) {
      await sendTelegram(env, text, "feed", opts.drill);
    }
    if (buyers.some((b) => b.isSignal)) await sendTelegram(env, text, "signal", opts.drill);
    await logAlert(env, "cluster", buy.mint, buyers.length, scoreCluster(buyers).score,
                   buyers.map((b) => b.name));
    sent += 1;
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
    // Heartbeat: without it, a quiet scan and a scan that never ran look the
    // same from outside.
    await env.DB.prepare(
      "INSERT OR REPLACE INTO sent (key, ts) VALUES ('heartbeat', ?)",
    ).bind(Date.now()).run();
    console.log(`poll slice ${slice}/${slices}: scanned ${result.scanned}, buys ${result.found}`);
  },

  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/hook" && request.method === "POST") {
      return handleWebhook(request, env);
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
      return Response.json({ signal: ok, feed: feedOk });
    }
    const counts = await env.DB.prepare(
      "SELECT (SELECT COUNT(*) FROM buys) AS buys, (SELECT COUNT(*) FROM alerts) AS alerts",
    ).first();
    const hb = await env.DB.prepare("SELECT ts FROM sent WHERE key = 'heartbeat'").first();
    return Response.json({
      status: "ok",
      tracking: TRACKED_SET.size,
      feed: FEED_SET.size,
      last_scan_seconds_ago: hb ? Math.round((Date.now() - hb.ts) / 1000) : null,
      buys_recorded: counts?.buys ?? 0,
      alerts_sent: counts?.alerts ?? 0,
    });
  },
};
