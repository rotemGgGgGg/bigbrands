/**
 * Market cap, from two independent public APIs — neither needs a key.
 *
 * One source was not enough. DexScreener rate limits by IP, and this worker
 * shares its IPs with the rest of the platform, so a 429 arrives because of
 * the neighbours and says nothing about the token. That turned a third
 * party's throttle into a silent gate on the rarest channel.
 *
 * So the question is asked twice, of two different providers, and the caller
 * is told which of three things came back: a number, a confident "this token
 * is too new to be listed anywhere", or a genuine unknown. Only the last is
 * ambiguous, and with two providers it is rare.
 */
const TIMEOUT_MS = 2500;
const CACHE_MS = 60_000;
const cache = new Map(); // mint -> { at, result }

/** @returns {{mc:number|null, listed:boolean}} or throws if the source failed. */
async function fromDexScreener(mint) {
  const resp = await fetch(`https://api.dexscreener.com/latest/dex/tokens/${mint}`,
    { signal: AbortSignal.timeout(TIMEOUT_MS) });
  if (!resp.ok) throw new Error(`dexscreener ${resp.status}`);
  const pairs = (await resp.json())?.pairs || [];
  if (!pairs.length) return { mc: null, listed: false };
  // Deepest pair is the one that prices the token; the thin ones lie.
  const best = pairs.reduce((a, b) =>
    (b.liquidity?.usd || 0) > (a.liquidity?.usd || 0) ? b : a);
  return {
    mc: best.marketCap ?? best.fdv ?? null,
    listed: true,
    liquidity: best.liquidity?.usd ?? null,
    ageMinutes: best.pairCreatedAt
      ? Math.round((Date.now() - best.pairCreatedAt) / 60_000) : null,
  };
}

async function fromJupiter(mint) {
  const resp = await fetch(`https://lite-api.jup.ag/tokens/v2/search?query=${mint}`,
    { signal: AbortSignal.timeout(TIMEOUT_MS) });
  if (!resp.ok) throw new Error(`jupiter ${resp.status}`);
  const body = await resp.json();
  const t = Array.isArray(body) ? body[0] : body;
  if (!t) return { mc: null, listed: false };
  return {
    mc: t.mcap ?? t.fdv ?? null,
    listed: true,
    liquidity: t.liquidity ?? null,
    ageMinutes: null,
  };
}

export async function marketCap(mint) {
  const hit = cache.get(mint);
  if (hit && Date.now() - hit.at < CACHE_MS) return hit.result;

  const failures = [];
  let sawUnlisted = false;
  for (const source of [fromDexScreener, fromJupiter]) {
    let answer;
    try {
      answer = await source(mint);
    } catch (err) {
      failures.push(err.message);
      continue;
    }
    if (answer.mc != null) {
      const result = { ...answer, known: true, notIndexed: false, reason: null };
      cache.set(mint, { at: Date.now(), result });
      return result;
    }
    // A clean answer with nothing in it means nobody lists this token yet.
    sawUnlisted = true;
  }

  const result = sawUnlisted
    ? { mc: null, known: true, notIndexed: true, reason: "not listed anywhere yet" }
    : { mc: null, known: false, notIndexed: false, reason: failures.join(", ") };
  if (sawUnlisted) cache.set(mint, { at: Date.now(), result });
  return result;
}
