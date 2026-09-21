/**
 * Market cap, from DexScreener's public API — no key, no quota to exhaust.
 *
 * Only the Legends gate calls this, and only for buys that already cleared
 * every other bar, so the extra round trip costs nothing on the common path.
 *
 * The caller must be able to tell a token that is genuinely too new to be
 * indexed from a lookup that simply failed. They look identical — no number
 * either way — but the first has every dollar of headroom and the second
 * could be anything, so they cannot be allowed to mean the same thing.
 */
const TIMEOUT_MS = 2000;
const CACHE_MS = 60_000;
const cache = new Map(); // mint -> { at, result }

async function lookup(mint) {
  const resp = await fetch(`https://api.dexscreener.com/latest/dex/tokens/${mint}`, {
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });
  if (!resp.ok) throw new Error(`http ${resp.status}`);
  return resp.json();
}

export async function marketCap(mint) {
  const hit = cache.get(mint);
  if (hit && Date.now() - hit.at < CACHE_MS) return hit.result;

  let data;
  try {
    data = await lookup(mint);
  } catch (first) {
    // A rate limit or a slow answer is worth one more try; a second failure
    // is an unknown, and an unknown is not a green light.
    try {
      data = await lookup(mint);
    } catch (err) {
      return { mc: null, known: false, notIndexed: false, reason: `${first.message} / ${err.message}` };
    }
  }

  const pairs = data?.pairs || [];
  if (!pairs.length) {
    const result = { mc: null, known: true, notIndexed: true, reason: "not indexed yet" };
    cache.set(mint, { at: Date.now(), result });
    return result;
  }

  // Deepest pair is the one that prices the token; the thin ones lie.
  const best = pairs.reduce((a, b) =>
    (b.liquidity?.usd || 0) > (a.liquidity?.usd || 0) ? b : a);

  // For a memecoin the whole supply is circulating, so fdv is the honest
  // number when marketCap is missing.
  const mc = best.marketCap ?? best.fdv ?? null;
  const result = {
    mc,
    known: mc != null,
    notIndexed: false,
    liquidity: best.liquidity?.usd ?? null,
    ageMinutes: best.pairCreatedAt
      ? Math.round((Date.now() - best.pairCreatedAt) / 60_000) : null,
    reason: mc == null ? "no market cap reported" : null,
  };
  cache.set(mint, { at: Date.now(), result });
  return result;
}
