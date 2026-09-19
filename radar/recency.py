"""Measure each candidate's activity in the recent past, not its historic pace.

The first selection used transactions-per-day derived from the span of a
wallet's last 100 transactions. A wallet that made those 100 in a burst a month
ago scored as active and has not traded since — which is why a list of twenty
produced no alerts. This counts transactions inside a fixed recent window
instead, which is the thing that actually predicts whether alerts will arrive.
"""
import argparse
import concurrent.futures
import json
import time

import requests

import config
import solana

ENDPOINT = "https://api.helius.xyz/v0/addresses/{}/transactions"


def recent_count(address: str, limiter, cutoff: float, pages: int = 3) -> int:
    """Transactions newer than `cutoff`, walking back until we pass it."""
    total, before = 0, None
    for _ in range(pages):
        params = {"api-key": config.HELIUS_API_KEY, "limit": 100}
        if before:
            params["before"] = before
        limiter.acquire()
        for attempt in range(4):
            try:
                resp = requests.get(ENDPOINT.format(address), params=params, timeout=30)
            except requests.RequestException:
                time.sleep(2 ** attempt)
                continue
            if resp.status_code == 200:
                break
            if resp.status_code in (429, 500, 502, 503, 504):
                time.sleep(2 ** attempt)
                continue
            return total
        else:
            return total
        batch = resp.json()
        if not isinstance(batch, list) or not batch:
            return total
        fresh = [t for t in batch if (t.get("timestamp") or 0) >= cutoff]
        total += len(fresh)
        if len(fresh) < len(batch) or len(batch) < 100:
            return total
        before = batch[-1]["signature"]
    return total


def main():
    parser = argparse.ArgumentParser(description="Measure recent wallet activity")
    parser.add_argument("--ranking", default="ranking_all.json")
    parser.add_argument("--days", type=float, default=7.0)
    parser.add_argument("--min-positions", type=int, default=15)
    parser.add_argument("--min-deployed", type=float, default=20.0)
    parser.add_argument("--all", action="store_true",
                        help="include wallets regardless of profit (for the wide feed)")
    parser.add_argument("--pages", type=int, default=3,
                        help="pages of 100 transactions to walk back; 1 is enough to answer "
                             "'did this wallet trade recently'")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--out", default="recency.json")
    args = parser.parse_args()

    ranking = json.loads(open(args.ranking).read())
    if args.all:
        candidates = list(ranking)
    else:
        candidates = [
            r for r in ranking
            if r.get("positions", 0) >= args.min_positions
            and r.get("net_sol", 0) > 0
            and r.get("sol_deployed", 0) >= args.min_deployed
        ]
    print(f"{len(candidates)} profitable candidates; counting last {args.days:g} days of activity…")

    limiter = solana.RateLimiter(config.RPC_RPS)
    cutoff = time.time() - args.days * 86400

    def measure(row):
        row = dict(row)
        row["recent_txs"] = recent_count(row["address"], limiter, cutoff, args.pages)
        row["recent_per_day"] = round(row["recent_txs"] / args.days, 2)
        return row

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for i, row in enumerate(pool.map(measure, candidates), 1):
            results.append(row)
            if i % 25 == 0:
                print(f"  {i}/{len(candidates)}", flush=True)

    json.dump(results, open(args.out, "w"), indent=2, ensure_ascii=False)
    live = [r for r in results if r["recent_txs"] > 0]
    print(f"\n{len(live)} of {len(results)} traded at all in the last {args.days:g} days")
    print(f"{sum(1 for r in results if r['recent_per_day'] >= 1)} average at least one trade a day")
    print(f"written to {args.out}")


if __name__ == "__main__":
    main()
