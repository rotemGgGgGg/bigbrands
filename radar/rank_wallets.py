"""Rank the tracked wallets by their own realised trading results.

The premise we never tested: that the 593 wallets on the list are actually
good. This pulls each wallet's recent history from Helius' parsed-transaction
endpoint (100 transactions per call, so the whole list costs well under 1% of
the free tier) and works out, per wallet, how its closed positions went.

A "position" is one mint: SOL spent acquiring it versus SOL received disposing
of it. Positions still open are excluded — an unsold bag is not a result.

Run: python rank_wallets.py [--limit N] [--out ranking.json]
"""
import argparse
import concurrent.futures
import json
import statistics
import time
from collections import defaultdict

import requests

import config
import solana
import wallets as wallets_mod

ENDPOINT = "https://api.helius.xyz/v0/addresses/{}/transactions"
LAMPORTS = 1_000_000_000
# Ignore the quote assets — moving SOL or USDC is not a position.
QUOTE_MINTS = config.IGNORED_MINTS


def fetch_history(address: str, limiter, pages: int = 2) -> list:
    """Most recent transactions, parsed, newest first."""
    out = []
    before = None
    for _ in range(pages):
        params = {"api-key": config.HELIUS_API_KEY, "limit": 100}
        if before:
            params["before"] = before
        limiter.acquire()
        try:
            resp = requests.get(ENDPOINT.format(address), params=params, timeout=30)
        except requests.RequestException:
            break
        if resp.status_code != 200:
            break
        batch = resp.json()
        if not isinstance(batch, list) or not batch:
            break
        out.extend(batch)
        before = batch[-1]["signature"]
        if len(batch) < 100:
            break
    return out


def wallet_deltas(tx: dict, wallet: str):
    """(sol_delta, {mint: token_delta}) for this wallet in one transaction."""
    sol_delta = 0.0
    tokens = defaultdict(float)
    for entry in tx.get("accountData", []):
        if entry.get("account") == wallet:
            sol_delta += (entry.get("nativeBalanceChange") or 0) / LAMPORTS
        for change in entry.get("tokenBalanceChanges") or []:
            if change.get("userAccount") != wallet:
                continue
            raw = change.get("rawTokenAmount") or {}
            try:
                amount = int(raw.get("tokenAmount", 0)) / (10 ** int(raw.get("decimals", 0)))
            except (TypeError, ValueError):
                continue
            mint = change.get("mint")
            if mint == solana.WSOL:
                sol_delta += amount
            elif mint:
                tokens[mint] += amount
    return sol_delta, tokens


def analyse(history: list, wallet: str) -> dict:
    """Per-mint SOL in/out, reduced to closed-position statistics."""
    spent = defaultdict(float)
    received = defaultdict(float)
    first_ts = {}

    for tx in history:
        if tx.get("transactionError"):
            continue
        sol_delta, tokens = wallet_deltas(tx, wallet)
        tokens = {m: d for m, d in tokens.items() if m not in QUOTE_MINTS and d != 0}
        if not tokens:
            continue
        acquired = [m for m, d in tokens.items() if d > 0]
        disposed = [m for m, d in tokens.items() if d < 0]
        if acquired and sol_delta < 0:
            for mint in acquired:
                spent[mint] += -sol_delta / len(acquired)
                first_ts.setdefault(mint, tx.get("timestamp", 0))
        if disposed and sol_delta > 0:
            for mint in disposed:
                received[mint] += sol_delta / len(disposed)

    closed = [m for m in spent if received.get(m, 0) > 0]
    if not closed:
        return {"positions": 0}

    returns = [(received[m] / spent[m] - 1) * 100 for m in closed]
    profit = sum(received[m] - spent[m] for m in closed)
    wins = [r for r in returns if r > 0]
    return {
        "positions": len(closed),
        "win_rate": round(100 * len(wins) / len(closed), 1),
        "median_return": round(statistics.median(returns), 1),
        "mean_return": round(sum(returns) / len(returns), 1),
        "net_sol": round(profit, 2),
        "sol_deployed": round(sum(spent[m] for m in closed), 2),
        "best": round(max(returns), 1),
        "worst": round(min(returns), 1),
    }


def main():
    parser = argparse.ArgumentParser(description="Rank tracked wallets by realised results")
    parser.add_argument("--limit", type=int, default=0, help="only the first N wallets")
    parser.add_argument("--pages", type=int, default=2, help="100 transactions per page")
    parser.add_argument("--min-positions", type=int, default=5,
                        help="hide wallets with fewer closed positions than this")
    parser.add_argument("--workers", type=int, default=8, help="parallel fetches")
    parser.add_argument("--out", default="ranking.json")
    args = parser.parse_args()

    wallet_list = wallets_mod.load_wallets()
    if args.limit:
        wallet_list = wallet_list[: args.limit]
    limiter = solana.RateLimiter(config.RPC_RPS)

    def scan(wallet):
        history = fetch_history(wallet["address"], limiter, args.pages)
        stats = analyse(history, wallet["address"])
        stats.update(
            {
                "address": wallet["address"],
                "name": f"{wallet['emoji']} {wallet['name']}".strip(),
                "txs_seen": len(history),
            }
        )
        return stats

    # The shared limiter still caps us at the plan's request rate; the pool only
    # hides per-request latency, which is what made the serial version crawl.
    results = []
    started = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for i, stats in enumerate(pool.map(scan, wallet_list), 1):
            results.append(stats)
            if i % 50 == 0:
                print(f"  {i}/{len(wallet_list)} ({int(time.time() - started)}s)", flush=True)

    with open(args.out, "w") as handle:
        json.dump(results, handle, indent=2)

    ranked = [r for r in results if r["positions"] >= args.min_positions]
    ranked.sort(key=lambda r: (r["median_return"], r["win_rate"]), reverse=True)

    print(f"\n{len(results)} wallets scanned · {len(ranked)} have >= "
          f"{args.min_positions} closed positions\n")
    print(f"{'name':<20} {'pos':>4} {'win%':>6} {'med%':>8} {'net SOL':>9} {'deployed':>9}")
    print("-" * 60)
    for row in ranked[:25]:
        print(f"{row['name'][:20]:<20} {row['positions']:>4} {row['win_rate']:>6.0f} "
              f"{row['median_return']:>8.0f} {row['net_sol']:>9.1f} {row['sol_deployed']:>9.1f}")

    if ranked:
        print("\nworst 5:")
        for row in ranked[-5:]:
            print(f"{row['name'][:20]:<20} {row['positions']:>4} {row['win_rate']:>6.0f} "
                  f"{row['median_return']:>8.0f} {row['net_sol']:>9.1f}")
        medians = [r["median_return"] for r in ranked]
        print(f"\nacross all qualifying wallets: median of medians "
              f"{statistics.median(medians):+.0f}%  ·  "
              f"profitable wallets {sum(1 for r in ranked if r['net_sol'] > 0)}/{len(ranked)}")
    print(f"\nfull results written to {args.out}")


if __name__ == "__main__":
    main()
