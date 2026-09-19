"""Pick the wallets worth following from the ranking.

Three filters, in order of how much each one mattered when we measured:

1. Profitable, with real size behind it — a good percentage on 2 SOL is noise.
2. Human pace. The most "consistent" wallets on the list turned out to be bots
   trading hundreds of times a day; nobody can follow a bot's fill, and it
   would bury the alerts.
3. Not a launcher. A token creator's profit comes from issuing the token, not
   from a trade we could copy.

Writes data/shortlist.json, which the radar loads instead of the full list.
"""
import argparse
import json
import time
from pathlib import Path

import requests

import config
import solana

ENDPOINT = "https://api.helius.xyz/v0/addresses/{}/transactions"
LAUNCHER_HINTS = ("dev", " test", "insider", "bundle")


def looks_like_launcher(name: str) -> bool:
    low = name.lower()
    return any(hint in low for hint in LAUNCHER_HINTS)


def trades_per_day(address: str, limiter) -> float:
    limiter.acquire()
    try:
        resp = requests.get(
            ENDPOINT.format(address),
            params={"api-key": config.HELIUS_API_KEY, "limit": 100},
            timeout=30,
        )
    except requests.RequestException:
        return -1.0
    if resp.status_code != 200:
        return -1.0
    batch = resp.json()
    if not isinstance(batch, list) or len(batch) < 2:
        return -1.0
    span_days = (batch[0]["timestamp"] - batch[-1]["timestamp"]) / 86400
    if span_days <= 0:
        return 9999.0
    return len(batch) / span_days


def main():
    parser = argparse.ArgumentParser(description="Select wallets worth following")
    parser.add_argument("--ranking", default="ranking.json")
    parser.add_argument("--out", default="data/shortlist.json")
    parser.add_argument("--min-positions", type=int, default=15)
    parser.add_argument("--min-deployed", type=float, default=20.0)
    parser.add_argument("--max-trades-day", type=float, default=10.0)
    parser.add_argument("--min-trades-day", type=float, default=0.15)
    args = parser.parse_args()

    ranking = json.loads(Path(args.ranking).read_text())
    candidates = [
        r
        for r in ranking
        if r.get("positions", 0) >= args.min_positions
        and r.get("net_sol", 0) > 0
        and r.get("sol_deployed", 0) >= args.min_deployed
        and not looks_like_launcher(r["name"])
    ]
    candidates.sort(key=lambda r: -r["net_sol"])
    print(f"{len(candidates)} profitable candidates; measuring trade pace…")

    limiter = solana.RateLimiter(config.RPC_RPS)
    chosen, too_fast, too_slow = [], [], []
    for row in candidates:
        pace = trades_per_day(row["address"], limiter)
        row["trades_per_day"] = round(pace, 2)
        if pace < 0:
            continue
        if pace > args.max_trades_day:
            too_fast.append(row)
        elif pace < args.min_trades_day:
            too_slow.append(row)
        else:
            chosen.append(row)

    chosen.sort(key=lambda r: -r["net_sol"])
    Path(args.out).write_text(json.dumps(chosen, indent=2, ensure_ascii=False))

    print(f"\nexcluded: {len(too_fast)} trading too fast to follow, "
          f"{len(too_slow)} effectively dormant\n")
    print(f"{'wallet':<24}{'pos':>4}{'win%':>6}{'net SOL':>9}{'trades/day':>12}")
    print("-" * 55)
    for row in chosen:
        print(f"{row['name'][:24]:<24}{row['positions']:>4}{row['win_rate']:>6.0f}"
              f"{row['net_sol']:>9.1f}{row['trades_per_day']:>12.1f}")
    total = sum(r["trades_per_day"] for r in chosen)
    print(f"\n{len(chosen)} wallets selected · roughly {total:.0f} trades/day between them")
    print(f"written to {args.out}")


if __name__ == "__main__":
    main()
