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
from pathlib import Path
from collections import defaultdict

import requests

import config
import solana
import wallets as wallets_mod

ENDPOINT = "https://api.helius.xyz/v0/addresses/{}/transactions"
LAMPORTS = 1_000_000_000
# Ignore the quote assets — moving SOL or USDC is not a position.
QUOTE_MINTS = config.IGNORED_MINTS


class FetchFailed(Exception):
    """A page could not be retrieved, so the history is incomplete."""


def _get_page(address: str, before, limiter, retries: int = 5):
    """One page, retrying through rate limits rather than silently giving up."""
    params = {"api-key": config.HELIUS_API_KEY, "limit": 100}
    if before:
        params["before"] = before
    backoff = 1.0
    for attempt in range(retries + 1):
        limiter.acquire()
        try:
            resp = requests.get(ENDPOINT.format(address), params=params, timeout=30)
        except requests.RequestException:
            if attempt == retries:
                raise FetchFailed("network")
            time.sleep(backoff)
            backoff *= 2
            continue
        if resp.status_code == 200:
            batch = resp.json()
            return batch if isinstance(batch, list) else []
        if resp.status_code in (429, 500, 502, 503, 504):
            if attempt == retries:
                raise FetchFailed(f"HTTP {resp.status_code}")
            time.sleep(backoff)
            backoff *= 2
            continue
        raise FetchFailed(f"HTTP {resp.status_code}")
    raise FetchFailed("retries exhausted")


def fetch_history(address: str, limiter, pages: int = 2) -> list:
    """Most recent transactions, parsed, newest first.

    Raises FetchFailed rather than returning a short history, so a wallet whose
    data could not be read is reported instead of scoring as inactive.
    """
    out = []
    before = None
    for _ in range(pages):
        batch = _get_page(address, before, limiter, retries=5)
        if not batch:
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
    parser.add_argument("--wallets", default="", help="path to a wallet list to rank instead of the default")
    parser.add_argument("--workers", type=int, default=8, help="parallel fetches")
    parser.add_argument("--out", default="ranking.json")
    args = parser.parse_args()

    if args.wallets:
        wallet_list = [
            {
                "address": w["trackedWalletAddress"],
                "name": w.get("name") or w["trackedWalletAddress"][:4],
                "emoji": w.get("emoji", ""),
                "priority": True,
            }
            for w in json.loads(Path(args.wallets).read_text())
            if w.get("trackedWalletAddress")
        ]
    else:
        wallet_list = wallets_mod.load_wallets()
    if args.limit:
        wallet_list = wallet_list[: args.limit]
    limiter = solana.RateLimiter(config.RPC_RPS)

    def scan(wallet):
        try:
            history = fetch_history(wallet["address"], limiter, args.pages)
        except FetchFailed as exc:
            return {
                "positions": 0,
                "address": wallet["address"],
                "name": f"{wallet['emoji']} {wallet['name']}".strip(),
                "txs_seen": 0,
                "error": str(exc),
            }
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

    failed = [r for r in results if r.get("error")]
    empty = [r for r in results if not r.get("error") and r["txs_seen"] == 0]
    if failed:
        print(f"\n!! {len(failed)} wallets could not be read "
              f"({failed[0]['error']}) — results below exclude them")
    print(f"{len(empty)} wallets returned no transactions at all")

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
