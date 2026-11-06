/**
 * Desk: where the bot reports, and where its owner looks.
 *
 * The bot runs elsewhere and only ever writes here; the page only ever reads.
 * Two keys keep those apart, so a phone that can see the ledger cannot write
 * to it, and the bot's key never has to sit in a browser.
 *
 * Paper trades are settled here, against real spot gold, on a schedule. A
 * paper order that is never settled is a number nobody can learn from, and
 * the bot has no price feed of its own to settle them with.
 */
import PAGE from "./page.html";
import { MANIFEST, ICON } from "./assets.js";
import { SW, subscribe, unsubscribe, notifyAll } from "./push.js";

const PIP = 0.1;

const json = (body, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", "cache-control": "no-store" },
  });

function bearer(req) {
  const h = req.headers.get("authorization") || "";
  return h.startsWith("Bearer ") ? h.slice(7).trim() : "";
}

/** Constant-time compare, so a key cannot be guessed a character at a time. */
function same(a, b) {
  if (!a || !b || a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

const now = () => Math.floor(Date.now() / 1000);

/** The "you are in a trade" notification. */
function entered(t, id) {
  const risk = Math.abs(Number(t.entry) - Number(t.sl)) * Number(t.units);
  return {
    title: `\uD83D\uDFE2 In a trade: ${String(t.side).toUpperCase()} ${t.units} oz @ ${Number(t.entry).toFixed(2)}`,
    body: `SL ${Number(t.sl).toFixed(2)} \u00B7 TP ${Number(t.tp).toFixed(2)} \u00B7 risk $${risk.toFixed(0)}`,
    tag: `trade-${id}`, url: "/#trades",
  };
}

function settle(t, exit, outcome, ts, note = null) {
  const move = t.side === "buy" ? exit - t.entry : t.entry - exit;
  return {
    exit,
    outcome,
    closed_at: ts,
    pips: Math.round((move / PIP) * 10) / 10,
    // One unit of XAU_USD is one ounce: a dollar of movement is a dollar.
    pnl: Math.round(move * t.units * 100) / 100,
    note,
  };
}

const px = (v) => (v === null || v === undefined ? "?" : Number(v).toFixed(2).replace(/\.?0+$/, ""));
const ORDER = { market: "", buy_stop: " STOP", sell_stop: " STOP", stop: " STOP", limit: " LIMIT", buy_limit: " LIMIT", sell_limit: " LIMIT" };
const orderWord = (o) => (o && ORDER[o] !== undefined ? ORDER[o] : o && o !== "market" ? ` ${String(o).toUpperCase()}` : "");

/** Pushes a notification without holding up the bot's request. */
function push(env, ctx, msg) {
  const job = notifyAll(env, msg).then((r) => console.log("push", JSON.stringify({ tag: msg.tag, sent: r.sent })))
    .catch((e) => console.log("push failed", String(e)));
  if (ctx) ctx.waitUntil(job);
  return job;
}

async function ingest(req, env, ctx) {
  const ev = await req.json().catch(() => null);
  if (!ev || !ev.type) return json({ error: "bad event" }, 400);
  const ts = Number(ev.ts) || now();

  if (ev.type === "signal") {
    const r = await env.DB.prepare(
      `INSERT INTO signals (ts, side, order_type, entry, sl, tp, status, reason, raw)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    ).bind(ts, ev.side ?? null, ev.order_type ?? null, ev.entry ?? null, ev.sl ?? null,
      ev.tp ?? null, ev.status || "skipped", ev.reason ?? null, (ev.raw || "").slice(0, 2000)).run();
    const status = ev.status || "skipped";
    const what = status === "taken" ? "\u2705 Copied" : status === "failed" ? "\u274C Failed" : "\u23ED\uFE0F Not copied";
    push(env, ctx, {
      title: `\uD83D\uDCE1 Signal: ${String(ev.side || "?").toUpperCase()}${orderWord(ev.order_type)} ${px(ev.entry)}`,
      body: `SL ${px(ev.sl)} \u00B7 TP ${px(ev.tp)}\n${what}${ev.reason ? `: ${String(ev.reason).slice(0, 140)}` : ""}`,
      tag: `signal-${r.meta.last_row_id}`, url: "/#signals",
    });
    return json({ ok: true, id: r.meta.last_row_id });
  }

  if (ev.type === "open") {
    for (const k of ["side", "units", "entry", "sl", "tp"]) {
      if (ev[k] === undefined || ev[k] === null) return json({ error: `missing ${k}` }, 400);
    }
    const order = ev.order_type || "market";
    // A market order is in the moment it is sent; anything else waits for
    // price to come to it, on paper and at a broker alike.
    const live = ev.mode === "live";
    const state = order === "market" ? "open" : "pending";
    const r = await env.DB.prepare(
      `INSERT INTO trades (signal_id, mode, side, order_type, units, entry, sl, tp,
                           created_at, opened_at, state)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    ).bind(ev.signal_id ?? null, live ? "live" : "paper", ev.side, order, Math.abs(ev.units),
      ev.entry, ev.sl, ev.tp, ts, state === "open" ? ts : null, state).run();
    // A market order is a trade entered now; a pending one is announced
    // when it fills.
    if (state === "open") push(env, ctx, entered({ ...ev, units: Math.abs(ev.units) }, r.meta.last_row_id));
    return json({ ok: true, id: r.meta.last_row_id });
  }

  if (ev.type === "fill") {
    await env.DB.prepare("UPDATE trades SET state='open', opened_at=?, entry=COALESCE(?, entry) WHERE id = ?")
      .bind(ts, ev.entry ?? null, ev.trade_id).run();
    const t = await env.DB.prepare("SELECT * FROM trades WHERE id = ?").bind(ev.trade_id).first();
    if (t) push(env, ctx, entered(t, t.id));
    return json({ ok: true });
  }

  if (ev.type === "be") {
    await env.DB.prepare("UPDATE trades SET sl=?, note=? WHERE id = ?")
      .bind(ev.sl, `stop moved to break-even +$1 at ${new Date(ts * 1000).toISOString().slice(11, 16)}Z`, ev.trade_id).run();
    return json({ ok: true });
  }

  if (ev.type === "trail") {
    // The stop pulled a dollar closer for each dollar in profit, up to the entry.
    await env.DB.prepare("UPDATE trades SET sl=?, note=? WHERE id = ?")
      .bind(ev.sl, ev.at_entry ? "stop on the entry" : `stop pulled to ${ev.sl}`, ev.trade_id).run();
    return json({ ok: true });
  }

  if (ev.type === "lock") {
    // Part of the target locked in as price neared it.
    await env.DB.prepare("UPDATE trades SET sl=?, note=? WHERE id = ?")
      .bind(ev.sl, `${ev.locked_pct}% of the target locked, stop ${ev.sl}`, ev.trade_id).run();
    const t = await env.DB.prepare("SELECT * FROM trades WHERE id = ?").bind(ev.trade_id).first();
    if (t) {
      const got = Math.abs(Number(ev.sl) - Number(t.entry)) * Number(t.units);
      push(env, ctx, { title: `\uD83D\uDCB0 Profit locked: $${got.toFixed(0)}`,
        body: `${String(t.side).toUpperCase()} ${t.units} oz from ${Number(t.entry).toFixed(2)}: stop now ${Number(ev.sl).toFixed(2)} (${ev.locked_pct}% of the target)`,
        tag: `trade-${t.id}`, url: "/#trades" });
    }
    return json({ ok: true });
  }

  if (ev.type === "expire") {
    await env.DB.prepare("UPDATE trades SET state='expired', closed_at=? WHERE id = ?")
      .bind(ts, ev.trade_id).run();
    return json({ ok: true });
  }

  if (ev.type === "close") {
    const t = await env.DB.prepare("SELECT * FROM trades WHERE id = ?").bind(ev.trade_id).first();
    if (!t) return json({ error: "no such trade" }, 404);
    const s = settle(t, Number(ev.exit), ev.outcome || "manual", ts, ev.note ?? null);
    // A broker knows the real result, after spread and commission; when it
    // reports one, that is the number kept.
    if (typeof ev.profit === "number") s.pnl = Math.round(ev.profit * 100) / 100;
    await env.DB.prepare(
      `UPDATE trades SET state='closed', exit=?, outcome=?, closed_at=?, pips=?, pnl=?, note=?
       WHERE id = ?`,
    ).bind(s.exit, s.outcome, s.closed_at, s.pips, s.pnl, s.note, t.id).run();
    return json({ ok: true, ...s });
  }

  if (ev.type === "heartbeat") {
    const payload = { mode: ev.mode || "paper", source: ev.source || null,
                      account: ev.account || null, rules: ev.rules || null };
    await env.DB.prepare(
      "INSERT INTO meta (k, v, ts) VALUES ('bot', ?, ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v, ts=excluded.ts",
    ).bind(JSON.stringify(payload), ts).run();
    // A limit the bot reached pauses copying here, where only the owner's
    // resume lifts it.
    if (ev.halt) await setControl(env, { paused: true, at: ts, reason: String(ev.halt).slice(0, 300) });
    // The answer carries the desk's instructions, so a pause pressed on a
    // phone reaches the bot within one heartbeat.
    const ctl = await env.DB.prepare("SELECT v FROM meta WHERE k = 'control'").first();
    // flatten_at is always present: a bot seeing it for the first time takes
    // it as the baseline, so the first real press is newer and is carried out.
    return json({ ok: true, flatten_at: 1, ...(ctl ? JSON.parse(ctl.v) : { paused: false }) });
  }

  if (ev.type === "flattened") {
    // The bot's own account of a close-all: what it closed and what failed.
    const lines = Array.isArray(ev.lines) ? ev.lines.map((l) => String(l).slice(0, 200)).slice(0, 20) : [];
    await setControl(env, { flat_result: { at: ts, lines } });
    return json({ ok: true });
  }

  return json({ error: `unknown type ${ev.type}` }, 400);
}

// The desk's instructions to the bot, kept as one record. Every change merges
// into it, so pausing does not forget a close-all press and the other way round.
async function setControl(env, patch) {
  const row = await env.DB.prepare("SELECT v FROM meta WHERE k = 'control'").first();
  const v = { ...(row ? JSON.parse(row.v) : { paused: false }), ...patch };
  await env.DB.prepare(
    "INSERT INTO meta (k, v, ts) VALUES ('control', ?, ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v, ts=excluded.ts",
  ).bind(JSON.stringify(v), now()).run();
  return v;
}

async function data(env) {
  const [signals, trades, bot, ctl] = await Promise.all([
    env.DB.prepare("SELECT * FROM signals ORDER BY ts DESC LIMIT 300").all(),
    env.DB.prepare("SELECT * FROM trades ORDER BY created_at DESC LIMIT 1000").all(),
    env.DB.prepare("SELECT v, ts FROM meta WHERE k = 'bot'").first(),
    env.DB.prepare("SELECT v FROM meta WHERE k = 'control'").first(),
  ]);
  return json({
    now: now(),
    bot: bot ? { ...JSON.parse(bot.v), ts: bot.ts } : null,
    control: ctl ? JSON.parse(ctl.v) : { paused: false },
    signals: signals.results || [],
    trades: trades.results || [],
  });
}

/**
 * Settles paper trades against real one-minute spot gold.
 *
 * A pending order fills the first minute price reaches it, and expires after
 * EXPIRE_MIN if it never does. An open trade closes on the first minute its
 * target or stop is touched. When one minute touches both, the order inside
 * it is not in the data, so the stop is assumed: a paper record that flatters
 * itself is worse than none.
 */
const EXPIRE_MIN = 240;
// The price service returns at most 5,000 minutes, and when a range is longer
// it silently returns the END of it. A trade from last week settled against
// this week's prices would close at the wrong time and price, so the range
// is walked forward a chunk per run, and each trade remembers how far it has
// been checked.
const CHUNK_S = 4800 * 60;

async function resolvePaper(env) {
  if (!env.TWELVEDATA_KEY) return { skipped: "no price key" };
  const { results } = await env.DB.prepare(
    "SELECT * FROM trades WHERE mode = 'paper' AND state IN ('pending', 'open')",
  ).all();
  if (!results || !results.length) return { open: 0 };

  const cursor = (t) => t.checked_to || (t.opened_at || t.created_at) - 60;
  const from = Math.min(...results.map(cursor));
  const to = Math.min(now(), from + CHUNK_S);
  const fmt = (s) => new Date(s * 1000).toISOString().slice(0, 19).replace("T", " ");
  const q = new URLSearchParams({
    symbol: "XAU/USD", interval: "1min", timezone: "UTC", order: "asc",
    start_date: fmt(from), end_date: fmt(to), outputsize: "5000",
    apikey: env.TWELVEDATA_KEY,
  });
  const res = await fetch(`https://api.twelvedata.com/time_series?${q}`);
  const body = await res.json();
  if (body.status === "error" && !/no data/i.test(body.message || "")) return { error: body.message };
  const bars = (body.values || []).map((v) => ({
    t: Date.parse(v.datetime.replace(" ", "T") + "Z") / 1000,
    o: Number(v.open), h: Number(v.high), l: Number(v.low),
  }));
  // An empty chunk is a closed market (a weekend), not an error: step past it.
  const reached = bars.length ? bars[bars.length - 1].t : to;

  let changed = 0;
  for (const t of results) {
    if (cursor(t) > to) continue;               // not reached by this chunk yet
    let state = t.state;
    let opened = t.opened_at;
    let done = null;
    let entry = t.entry;
    let note = null;

    // A market order fills at whatever gold costs that minute, not at the
    // number in the message. Paper has to do the same or it is grading a
    // trade nobody could have taken. Done once, on the first look.
    if (state === "open" && t.order_type === "market" && !t.checked_to) {
      const first = bars.find((b) => b.t >= t.created_at - 59);
      if (first) {
        entry = first.o;
        opened = first.t;
        const past = t.side === "buy"
          ? (entry <= t.sl ? "stop" : entry >= t.tp ? "target" : null)
          : (entry >= t.sl ? "stop" : entry <= t.tp ? "target" : null);
        if (past) {
          state = "expired";
          note = `price ${entry.toFixed(2)} was already past the ${past} when the signal arrived`;
        }
      }
    }
    const live = { ...t, entry };

    for (let i = 0; i < bars.length && state !== "expired"; i++) {
      const b = bars[i];
      if (b.t <= cursor(t) || b.t < t.created_at - 60) continue;
      if (state === "pending") {
        if (b.t > t.created_at + EXPIRE_MIN * 60) { state = "expired"; break; }
        const prev = bars[i - 1];
        let filled;
        if (t.order_type === "stop") {
          // A stop fills on a break through the level, not on a visit to it.
          filled = t.side === "buy"
            ? b.h >= t.entry && (!prev || prev.h < t.entry)
            : b.l <= t.entry && (!prev || prev.l > t.entry);
        } else {
          filled = b.l <= t.entry && t.entry <= b.h;
        }
        if (!filled) continue;
        state = "open";
        opened = b.t;
      }
      if (state === "open") {
        if (b.t < opened) continue;
        const hitTp = t.side === "buy" ? b.h >= t.tp : b.l <= t.tp;
        const hitSl = t.side === "buy" ? b.l <= t.sl : b.h >= t.sl;
        if (hitSl) { done = settle(live, t.sl, "sl", b.t, hitTp ? "tp and sl in one minute; stop assumed" : null); break; }
        if (hitTp) { done = settle(live, t.tp, "tp", b.t); break; }
      }
    }
    if (state === "pending" && reached > t.created_at + EXPIRE_MIN * 60) state = "expired";

    if (done) {
      await env.DB.prepare(
        `UPDATE trades SET state='closed', entry=?, opened_at=?, exit=?, outcome=?, closed_at=?, pips=?, pnl=?, note=?, checked_to=?
         WHERE id = ?`,
      ).bind(entry, opened, done.exit, done.outcome, done.closed_at, done.pips, done.pnl, done.note, done.closed_at, t.id).run();
    } else {
      await env.DB.prepare("UPDATE trades SET state=?, entry=?, opened_at=?, checked_to=?, note=COALESCE(?, note) WHERE id = ?")
        .bind(state, entry, opened, reached, note, t.id).run();
    }
    changed++;
  }
  return { checked: results.length, changed, window: [fmt(from), fmt(reached)], bars: bars.length };
}

/**
 * The watchdog. It runs here and not in the bot, because a bot that has
 * crashed cannot report that it crashed. If the bot has not been heard from
 * in a few minutes, its owner's phone hears about it, once, and hears again
 * when it comes back.
 */
const SILENT_AFTER_S = 180;

async function telegram(env, text) {
  if (!env.ALERT_BOT_TOKEN || !env.ALERT_CHAT_ID) return;
  await fetch(`https://api.telegram.org/bot${env.ALERT_BOT_TOKEN}/sendMessage`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ chat_id: env.ALERT_CHAT_ID, text, parse_mode: "HTML" }),
  }).catch(() => {});
}

async function watchdog(env) {
  const bot = await env.DB.prepare("SELECT v, ts FROM meta WHERE k = 'bot'").first();
  if (!bot) return { watching: false };
  const flag = await env.DB.prepare("SELECT v FROM meta WHERE k = 'alarm'").first();
  const silent = now() - bot.ts;
  const raised = flag && flag.v === "on";
  if (silent > SILENT_AFTER_S && !raised) {
    await telegram(env, `\u26A0\uFE0F <b>Tape bot is silent</b>\nNo sign of life for ${Math.round(silent / 60)} minutes. Trades are not being copied.`);
    await env.DB.prepare("INSERT INTO meta (k, v, ts) VALUES ('alarm', 'on', ?) ON CONFLICT(k) DO UPDATE SET v='on', ts=excluded.ts").bind(now()).run();
  } else if (silent <= SILENT_AFTER_S && raised) {
    await telegram(env, "\u2705 <b>Tape bot is back</b> and listening again.");
    await env.DB.prepare("UPDATE meta SET v='off', ts=? WHERE k='alarm'").bind(now()).run();
  }
  return { silent, raised };
}

/**
 * Price around one trade, for its chart: from a little before it opened to a
 * little after it closed, at a bar size that keeps it near 120 bars. A closed
 * trade's bars never change, so they are kept after the first fetch.
 */
async function candles(env, id) {
  const t = await env.DB.prepare("SELECT * FROM trades WHERE id = ?").bind(id).first();
  if (!t) return { error: "no such trade" };
  const key = `candles2:${id}`;
  if (t.state === "closed" || t.state === "expired") {
    const hit = await env.DB.prepare("SELECT v FROM meta WHERE k = ?").bind(key).first();
    if (hit) return JSON.parse(hit.v);
  }
  if (!env.TWELVEDATA_KEY) return { error: "no price key" };
  const start = t.opened_at || t.created_at;
  const end = t.closed_at || now();
  const span = Math.max(end - start, 600);
  const pad = Math.max(900, Math.round(span * 0.35));
  const from = start - pad, to = Math.min(now(), end + pad);
  const sizes = [1, 5, 15, 30, 60, 240];
  const step = sizes.find((m) => (to - from) / 60 / m <= 140) || 240;
  const interval = step >= 60 ? `${step / 60}h` : `${step}min`;
  const fmt = (x) => new Date(x * 1000).toISOString().slice(0, 19).replace("T", " ");
  const q = new URLSearchParams({ symbol: "XAU/USD", interval, timezone: "UTC", order: "asc",
    start_date: fmt(from), end_date: fmt(to), outputsize: "5000", apikey: env.TWELVEDATA_KEY });
  const body = await (await fetch(`https://api.twelvedata.com/time_series?${q}`)).json();
  if (body.status === "error") return { error: body.message || "price source refused" };
  const bars = (body.values || []).map((v) => [Date.parse(v.datetime.replace(" ", "T") + "Z") / 1000,
    +v.open, +v.high, +v.low, +v.close]);
  const out = { id: t.id, interval, bars };
  if ((t.state === "closed" || t.state === "expired") && bars.length) {
    await env.DB.prepare("INSERT INTO meta (k, v, ts) VALUES (?, ?, ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v, ts=excluded.ts")
      .bind(key, JSON.stringify(out), now()).run();
  }
  return out;
}

/**
 * One-time repair: until 6 Nov 2026 the bot sent MT5 fill and close times in
 * the broker's clock (UTC+2, UTC+3 before 1 Nov), so those trades sat hours
 * late on the desk. These are the corrected UTC times; it runs once.
 */
const TZ_FIX = [{"id": 18, "closed_at": 1793967482, "opened_at": 1793965626}, {"id": 17, "closed_at": 1793964234, "opened_at": 1793959845}, {"id": 16, "closed_at": 1793892829, "opened_at": 1793892366}, {"id": 15, "closed_at": 1793889483}, {"id": 14, "closed_at": 1793886024, "opened_at": 1793884209}, {"id": 13, "closed_at": 1793886496}, {"id": 12, "closed_at": 1793804534, "opened_at": 1793803837}, {"id": 11, "closed_at": 1793802765}, {"id": 10, "closed_at": 1793797394}, {"id": 9, "closed_at": 1793794810, "opened_at": 1793793871}, {"id": 8, "closed_at": 1793712582}, {"id": 7, "closed_at": 1793634368, "opened_at": 1793633408}, {"id": 6, "closed_at": 1793629616}, {"id": 5, "closed_at": 1793628957}, {"id": 4, "closed_at": 1793626903, "opened_at": 1793625793}, {"id": 3, "closed_at": 1793625603, "opened_at": 1793624462}, {"id": 2, "closed_at": 1793280862, "opened_at": 1793280797}];
async function fixTimesOnce(env) {
  const done = await env.DB.prepare("SELECT v FROM meta WHERE k = 'tzfix1'").first();
  if (done) return;
  for (const f of TZ_FIX) {
    await env.DB.prepare("UPDATE trades SET opened_at = COALESCE(?, opened_at), closed_at = ? WHERE id = ? AND mode = 'live'")
      .bind(f.opened_at ?? null, f.closed_at, f.id).run();
  }
  await env.DB.prepare("INSERT INTO meta (k, v, ts) VALUES ('tzfix1', 'done', ?)").bind(now()).run();
  console.log("tzfix1 applied", TZ_FIX.length);
}

export default {
  async fetch(req, env, ctx) {
    const url = new URL(req.url);
    const path = url.pathname;

    if (req.method === "GET" && (path === "/" || path === "/index.html")) {
      return new Response(PAGE, {
        headers: {
          "content-type": "text/html; charset=utf-8",
          "cache-control": "no-cache",
          "x-frame-options": "DENY",
          "referrer-policy": "no-referrer",
        },
      });
    }
    if (path === "/manifest.webmanifest") {
      return new Response(MANIFEST, { headers: { "content-type": "application/manifest+json" } });
    }
    if (path === "/icon.svg") {
      return new Response(ICON, { headers: { "content-type": "image/svg+xml", "cache-control": "max-age=86400" } });
    }

    if (path === "/sw.js") {
      return new Response(SW, { headers: { "content-type": "text/javascript", "cache-control": "no-cache" } });
    }
    if (path.startsWith("/api/push/")) {
      if (!same(bearer(req), env.VIEW_KEY)) return json({ error: "unauthorized" }, 401);
      if (path === "/api/push/key") return json({ key: env.VAPID_PUBLIC || null });
      const body = req.method === "POST" ? await req.json().catch(() => ({})) : {};
      if (path === "/api/push/subscribe" && req.method === "POST") return json(await subscribe(env, body));
      if (path === "/api/push/unsubscribe" && req.method === "POST") return json(await unsubscribe(env, String(body.endpoint || "")));
      if (path === "/api/push/test" && req.method === "POST") {
        return json(await notifyAll(env, { title: "\uD83D\uDD14 Tape notifications are on",
          body: "You will hear about every VIP signal and every trade the bot enters.", tag: "test", url: "/" }));
      }
      return json({ error: "not found" }, 404);
    }
    if (path === "/api/event" && req.method === "POST") {
      if (!same(bearer(req), env.INGEST_KEY)) return json({ error: "unauthorized" }, 401);
      return ingest(req, env, ctx);
    }
    if (path === "/api/data" && req.method === "GET") {
      if (!same(bearer(req), env.VIEW_KEY)) return json({ error: "unauthorized" }, 401);
      return data(env);
    }
    if (path === "/api/candles" && req.method === "GET") {
      if (!same(bearer(req), env.VIEW_KEY)) return json({ error: "unauthorized" }, 401);
      const r = await candles(env, Number(url.searchParams.get("trade")));
      return json(r, r.error ? 404 : 200);
    }
    if (path === "/api/control" && req.method === "POST") {
      // What a viewer may change: whether the bot copies, and the emergency
      // close-all. Reading and recording go on regardless.
      if (!same(bearer(req), env.VIEW_KEY)) return json({ error: "unauthorized" }, 401);
      const body = await req.json().catch(() => ({}));
      if (body.flatten) {
        // Close everything: the bot closes positions and cancels its pending
        // orders at its next heartbeat, and copying pauses so nothing new opens.
        return json(await setControl(env, { paused: true, at: now(), reason: "closed everything from the desk",
                                            flatten_at: now(), flat_result: null }));
      }
      return json(await setControl(env, { paused: Boolean(body.paused), at: now(), reason: null }));
    }
    if (path === "/api/history" && req.method === "POST") {
      // A dump of the channel's past messages, sent in parts by export.py, so
      // the message formats can be studied without access to Telegram.
      if (!same(bearer(req), env.INGEST_KEY)) return json({ error: "unauthorized" }, 401);
      const body = await req.json().catch(() => ({}));
      const part = Math.max(0, Math.min(99, Number(body.part) || 0));
      await env.DB.prepare(
        "INSERT INTO meta (k, v, ts) VALUES (?, ?, ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v, ts=excluded.ts",
      ).bind(`history:${part}`, JSON.stringify({ parts: Number(body.parts) || 1, text: String(body.text || "").slice(0, 400000) }), now()).run();
      return json({ ok: true, part });
    }
    if (path === "/api/history" && req.method === "GET") {
      if (!same(bearer(req), env.VIEW_KEY)) return json({ error: "unauthorized" }, 401);
      const part = Math.max(0, Math.min(99, Number(url.searchParams.get("part")) || 0));
      const row = await env.DB.prepare("SELECT v, ts FROM meta WHERE k = ?").bind(`history:${part}`).first();
      return json(row ? { ts: row.ts, ...JSON.parse(row.v) } : { error: "none" }, row ? 200 : 404);
    }
    if (path === "/api/resolve" && req.method === "POST") {
      if (!same(bearer(req), env.INGEST_KEY)) return json({ error: "unauthorized" }, 401);
      return json(await resolvePaper(env));
    }
    return new Response("not found", { status: 404 });
  },

  async scheduled(event, env, ctx) {
    ctx.waitUntil(fixTimesOnce(env));
    // The watchdog every minute; paper settlement every fifth, which keeps
    // the free price allowance far from its daily limit.
    ctx.waitUntil(watchdog(env).then((r) => console.log("watchdog", JSON.stringify(r))));
    if (new Date(event.scheduledTime).getUTCMinutes() % 5 === 0) {
      ctx.waitUntil(resolvePaper(env).then((r) => console.log("resolve", JSON.stringify(r))));
    }
  },
};
