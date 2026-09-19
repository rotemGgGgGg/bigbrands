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
import { TRACKED } from "./wallets.js";

const TRACKED_SET = new Set(Object.keys(TRACKED));

function html(text) {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
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

async function sendTelegram(env, text) {
  if (!env.TELEGRAM_BOT_TOKEN || !env.TELEGRAM_CHAT_ID) return false;
  const resp = await fetch(
    `https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        chat_id: env.TELEGRAM_CHAT_ID,
        text,
        parse_mode: "HTML",
        disable_web_page_preview: true,
      }),
    },
  );
  return resp.ok;
}

async function handleWebhook(request, env) {
  // The webhook URL is effectively the credential, so it carries a secret.
  const url = new URL(request.url);
  if (!env.HOOK_SECRET || url.searchParams.get("s") !== env.HOOK_SECRET) {
    return new Response("forbidden", { status: 403 });
  }

  let payload;
  try {
    payload = await request.json();
  } catch {
    return new Response("bad json", { status: 400 });
  }
  const transactions = Array.isArray(payload) ? payload : [payload];

  const minSol = Number(env.MIN_SOL_BUY || "0.05");
  const reAlertMs = Number(env.RE_ALERT_MINUTES || "60") * 60_000;
  let alerted = 0;

  for (const tx of transactions) {
    for (const buy of extractBuys(tx, TRACKED_SET, minSol)) {
      // One alert per wallet+mint per window; a wallet adding to the same
      // position is not news.
      const key = `alerted:${buy.wallet}:${buy.mint}`;
      if (await env.STATE.get(key)) continue;
      await env.STATE.put(key, "1", { expirationTtl: Math.floor(reAlertMs / 1000) });

      const name = TRACKED[buy.wallet] || buy.wallet.slice(0, 6);
      const delivered = await sendTelegram(env, formatAlert(buy, name));
      await env.STATE.put(
        `alert:${Date.now()}:${buy.mint.slice(0, 8)}`,
        JSON.stringify({ ...buy, name, delivered, ts: Date.now() }),
        { expirationTtl: 30 * 24 * 3600 },
      );
      alerted += 1;
    }
  }

  return Response.json({ ok: true, transactions: transactions.length, alerted });
}

async function listAlerts(env) {
  const { keys } = await env.STATE.list({ prefix: "alert:", limit: 100 });
  const rows = [];
  for (const key of keys.reverse()) {
    const value = await env.STATE.get(key.name);
    if (value) rows.push(JSON.parse(value));
  }
  return Response.json({ count: rows.length, alerts: rows });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/hook" && request.method === "POST") {
      return handleWebhook(request, env);
    }
    if (url.pathname === "/alerts") return listAlerts(env);
    if (url.pathname === "/test") {
      const ok = await sendTelegram(env, "🟢 <b>Radar is live.</b>\nThis is a connection test.");
      return Response.json({ telegram: ok });
    }
    return Response.json({ status: "ok", tracking: TRACKED_SET.size });
  },
};
