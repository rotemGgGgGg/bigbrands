/**
 * Buy extraction and confluence scoring.
 *
 * Kept free of Cloudflare and Helius specifics so it can be unit tested with
 * plain objects, and so the rules stay comparable with the Python version.
 */

export const WSOL = "So11111111111111111111111111111111111111112";

export const IGNORED_MINTS = new Set([
  WSOL,
  "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", // USDC
  "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB", // USDT
  "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",  // mSOL
  "J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn", // jitoSOL
]);

const LAMPORTS_PER_SOL = 1_000_000_000;

/**
 * Pull buys out of one Helius enhanced-webhook transaction.
 *
 * Same rule as the polling version: a wallet we track ended up with more of
 * some token while net-spending SOL in the same transaction. That covers any
 * DEX route without per-DEX parsing, and excludes airdrops (nothing spent).
 */
export function extractBuys(tx, trackedSet, minSolBuy) {
  if (!tx || tx.transactionError) return [];

  const tokenTransfers = tx.tokenTransfers || [];
  const nativeTransfers = tx.nativeTransfers || [];

  // SOL spent per wallet: native out, plus wrapped-SOL out.
  const spent = new Map();
  const add = (wallet, amount) =>
    spent.set(wallet, (spent.get(wallet) || 0) + amount);

  for (const t of nativeTransfers) {
    if (t.fromUserAccount) add(t.fromUserAccount, (t.amount || 0) / LAMPORTS_PER_SOL);
    if (t.toUserAccount) add(t.toUserAccount, -(t.amount || 0) / LAMPORTS_PER_SOL);
  }
  for (const t of tokenTransfers) {
    if (t.mint !== WSOL) continue;
    const amount = Number(t.tokenAmount) || 0;
    if (t.fromUserAccount) add(t.fromUserAccount, amount);
    if (t.toUserAccount) add(t.toUserAccount, -amount);
  }

  // Tokens gained per (wallet, mint).
  const gained = new Map();
  for (const t of tokenTransfers) {
    const wallet = t.toUserAccount;
    if (!wallet || !trackedSet.has(wallet)) continue;
    if (!t.mint || IGNORED_MINTS.has(t.mint)) continue;
    const amount = Number(t.tokenAmount) || 0;
    if (amount <= 0) continue;
    const key = `${wallet}|${t.mint}`;
    gained.set(key, (gained.get(key) || 0) + amount);
  }

  const ts = tx.timestamp || Math.floor(Date.now() / 1000);
  const byWallet = new Map();
  for (const [key, amount] of gained) {
    const [wallet, mint] = key.split("|");
    if ((spent.get(wallet) || 0) < minSolBuy) continue;
    if (!byWallet.has(wallet)) byWallet.set(wallet, []);
    byWallet.get(wallet).push({ mint, amount });
  }

  const buys = [];
  for (const [wallet, entries] of byWallet) {
    // Split the SOL across mints so a multi-hop route is not double counted.
    const solEach = (spent.get(wallet) || 0) / entries.length;
    for (const entry of entries) {
      buys.push({
        sig: tx.signature,
        wallet,
        mint: entry.mint,
        ts,
        sol_spent: Number(solEach.toFixed(4)),
        amount: entry.amount,
      });
    }
  }
  return buys;
}

const clamp = (v, lo = 0, hi = 1) => Math.max(lo, Math.min(hi, v));

/** 0-100, weighted on breadth / speed / size / novelty. Price is not an input. */
export function scoreEvent(event, cfg) {
  const spanMin = Math.max(event.span_sec, 1) / 60;
  const ageMin = event.mint_age_sec / 60;

  const breadth = clamp((event.wallet_count - cfg.MIN_WALLETS + 1) / 6);
  const speed = clamp(1 - spanMin / cfg.WINDOW_MINUTES);
  const size = clamp(event.total_sol / 10);
  const novelty = ageMin > 5 ? clamp(1 - (ageMin - 5) / 55) : 1;

  return Math.round(100 * (0.4 * breadth + 0.25 * speed + 0.15 * size + 0.2 * novelty));
}

/** Group rows of buys by mint and return scored events meeting the rule. */
export function findEvents(rows, cfg, now) {
  const byMint = new Map();
  for (const row of rows) {
    if (!byMint.has(row.mint)) byMint.set(row.mint, []);
    byMint.get(row.mint).push(row);
  }

  const events = [];
  for (const [mint, buys] of byMint) {
    const wallets = [...new Set(buys.map((b) => b.wallet))].sort();
    if (wallets.length < cfg.MIN_WALLETS) continue;
    const times = buys.map((b) => b.ts);
    const firstSeen = buys[0].first_seen ?? Math.min(...times);
    const event = {
      mint,
      wallets,
      wallet_count: wallets.length,
      buy_count: buys.length,
      total_sol: Number(buys.reduce((sum, b) => sum + b.sol_spent, 0).toFixed(3)),
      span_sec: Math.max(...times) - Math.min(...times),
      mint_age_sec: now - firstSeen,
    };
    event.score = scoreEvent(event, cfg);
    events.push(event);
  }
  events.sort((a, b) => b.score - a.score);
  return events;
}
