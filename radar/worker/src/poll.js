/**
 * Fallback collection path: poll Solana's public RPC directly.
 *
 * The pushed feed needs a provider with quota, and when that runs out nothing
 * arrives at all. Public RPC needs no key and no account, so the radar can
 * keep working on its own — at up to a minute of delay instead of a fraction
 * of a second, and only for the selected wallets, because a scan costs calls
 * where a push costs nothing.
 */
// Public endpoints throttle hard, and each one throttles separately, so the
// scan spreads itself across several and starts at a different one each time.
const RPC_ENDPOINTS = [
  "https://solana-rpc.publicnode.com",
  "https://solana.drpc.org",
  "https://endpoints.omniatech.io/v1/sol/mainnet/public",
  "https://solana.api.onfinality.io/public",
];

const LAMPORTS = 1_000_000_000;
export const WSOL = "So11111111111111111111111111111111111111112";
const IGNORED = new Set([
  WSOL,
  "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
  "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
]);

let rpcCursor = 0;

async function rpc(method, params) {
  let lastError;
  const start = rpcCursor++ % RPC_ENDPOINTS.length;
  const order = RPC_ENDPOINTS.map((_, i) => RPC_ENDPOINTS[(start + i) % RPC_ENDPOINTS.length]);
  for (const url of order) {
    try {
      const resp = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params }),
      });
      if (!resp.ok) {
        lastError = new Error(`${url} -> HTTP ${resp.status}`);
        continue;
      }
      const data = await resp.json();
      if (data.error) {
        lastError = new Error(`${url} -> ${JSON.stringify(data.error).slice(0, 120)}`);
        continue;
      }
      return data.result;
    } catch (err) {
      lastError = err;
    }
  }
  throw lastError || new Error("no endpoint answered");
}

/** Buys by `owner` in a jsonParsed transaction: tokens up, SOL net spent. */
export function extractBuysRaw(tx, owner, minSol) {
  if (!tx || tx.meta?.err) return [];
  const meta = tx.meta;
  const keys = (tx.transaction?.message?.accountKeys || []).map((k) =>
    typeof k === "string" ? k : k.pubkey,
  );

  let solDelta = 0;
  const idx = keys.indexOf(owner);
  if (idx >= 0 && meta.preBalances?.[idx] != null && meta.postBalances?.[idx] != null) {
    solDelta = (meta.postBalances[idx] - meta.preBalances[idx]) / LAMPORTS;
  }

  const tokenMap = (entries) => {
    const out = new Map();
    for (const e of entries || []) {
      if (e.owner !== owner) continue;
      out.set(e.mint, Number(e.uiTokenAmount?.uiAmount) || 0);
    }
    return out;
  };
  const pre = tokenMap(meta.preTokenBalances);
  const post = tokenMap(meta.postTokenBalances);

  solDelta += (post.get(WSOL) || 0) - (pre.get(WSOL) || 0);
  const spent = -solDelta;
  if (spent < minSol) return [];

  const buys = [];
  for (const mint of new Set([...pre.keys(), ...post.keys()])) {
    if (IGNORED.has(mint)) continue;
    if ((post.get(mint) || 0) - (pre.get(mint) || 0) > 0) buys.push({ mint });
  }
  return buys.map((b) => ({
    ...b,
    wallet: owner,
    sol_spent: Number((spent / buys.length).toFixed(4)),
    ts: (tx.blockTime || Math.floor(Date.now() / 1000)) * 1000,
  }));
}

async function cursorFor(env, wallet) {
  const row = await env.DB.prepare("SELECT last_sig FROM cursors WHERE wallet = ?")
    .bind(wallet).first();
  return row?.last_sig || null;
}

/**
 * Scan a slice of wallets. Workers cap the subrequests one invocation may make,
 * so each run takes a slice and the whole set is covered over a few minutes.
 */
export async function pollSlice(env, wallets, sliceIndex, slices, minSol, onBuy) {
  const mine = wallets.filter((_, i) => i % slices === sliceIndex);
  let scanned = 0;
  let found = 0;

  for (const wallet of mine) {
    let sigs;
    try {
      const until = await cursorFor(env, wallet);
      const params = [wallet, until ? { limit: 10, until } : { limit: 1 }];
      sigs = await rpc("getSignaturesForAddress", params);
    } catch (err) {
      console.log(`sigs failed for ${wallet}: ${err.message}`);
      continue;
    }
    scanned += 1;
    if (!sigs?.length) continue;

    await env.DB.prepare(
      "INSERT INTO cursors (wallet, last_sig, updated_at) VALUES (?, ?, ?) " +
        "ON CONFLICT(wallet) DO UPDATE SET last_sig = excluded.last_sig, updated_at = excluded.updated_at",
    ).bind(wallet, sigs[0].signature, Date.now()).run();

    // A first sighting only sets the cursor; without it every wallet would
    // replay its history on the first run.
    const until = await cursorFor(env, wallet);
    if (!until) continue;

    for (const entry of sigs.slice(0, 4).reverse()) {
      if (entry.err) continue;
      let tx;
      try {
        tx = await rpc("getTransaction", [
          entry.signature,
          { encoding: "jsonParsed", maxSupportedTransactionVersion: 1, commitment: "confirmed" },
        ]);
      } catch {
        continue;
      }
      for (const buy of extractBuysRaw(tx, wallet, minSol)) {
        found += 1;
        await onBuy(buy, entry.signature);
      }
    }
  }
  return { scanned, found };
}
