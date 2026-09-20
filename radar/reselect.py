"""Rebuild the selected list from wallets that are both profitable and trading now.

The first selection ranked wallets on their last few hundred transactions
without asking when those happened, so a wallet whose good run ended two years
ago scored near the top and never fired. Recent activity is now a requirement,
not a tiebreak.
"""
import argparse
import concurrent.futures
import json
import time

import requests

import config
import solana

RPC = "https://chaotic-stylish-season.solana-mainnet.quiknode.pro/20876156c438a0d3da2fd572178f611de42f3c1e"


def launcher(name: str) -> bool:
    low = name.lower()
    return any(k in low for k in ("dev", " test", "insider", "bundle"))


def activity(address: str, limiter):
    """(hours since last trade, trades in 24h, trades in 7d)."""
    limiter.acquire()
    for attempt in range(4):
        try:
            resp = requests.post(RPC, json={
                "jsonrpc": "2.0", "id": 1, "method": "getSignaturesForAddress",
                "params": [address, {"limit": 100}],
            }, timeout=30)
        except requests.RequestException:
            time.sleep(2 ** attempt)
            continue
        if resp.status_code == 200:
            sigs = resp.json().get("result") or []
            break
        time.sleep(2 ** attempt)
    else:
        return None, 0, 0
    if not sigs:
        return None, 0, 0
    now = time.time()
    last = sigs[0].get("blockTime")
    return (
        (now - last) / 3600 if last else None,
        sum(1 for s in sigs if (s.get("blockTime") or 0) > now - 86400),
        sum(1 for s in sigs if (s.get("blockTime") or 0) > now - 7 * 86400),
    )


def main():
    parser = argparse.ArgumentParser(description="Reselect on profit and current activity")
    parser.add_argument("--ranking", default="ranking_all.json")
    parser.add_argument("--min-positions", type=int, default=15)
    parser.add_argument("--min-deployed", type=float, default=15.0)
    parser.add_argument("--min-week", type=int, default=3, help="minimum trades in the last week")
    parser.add_argument("--max-day", type=int, default=150, help="above this is a bot, not a trader")
    parser.add_argument("--keep", type=int, default=30)
    args = parser.parse_args()

    ranking = json.load(open(args.ranking))
    candidates = [
        r for r in ranking
        if r.get("positions", 0) >= args.min_positions
        and r.get("net_sol", 0) > 0
        and r.get("sol_deployed", 0) >= args.min_deployed
        and not launcher(r["name"])
    ]
    print(f"{len(candidates)} profitable candidates; checking who is still trading…")

    limiter = solana.RateLimiter(10)

    def check(row):
        row = dict(row)
        row["hours_since"], row["day"], row["week"] = activity(row["address"], limiter)
        return row

    rows = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for i, row in enumerate(pool.map(check, candidates), 1):
            rows.append(row)
            if i % 40 == 0:
                print(f"  {i}/{len(candidates)}", flush=True)

    live = [r for r in rows if r["week"] >= args.min_week and r["day"] <= args.max_day]
    live.sort(key=lambda r: -(100 * r["net_sol"] / r["sol_deployed"]))
    keep = live[: args.keep]

    json.dump(keep, open("data/shortlist.json", "w"), indent=2, ensure_ascii=False)
    print(f"\n{len(rows)} checked · {sum(1 for r in rows if r['week'] > 0)} traded this week · "
          f"{len(live)} also profitable and human-paced\n")
    print(f"{'wallet':<24}{'ROI%':>6}{'netSOL':>8}{'24h':>5}{'7d':>5}{'last':>8}")
    print("-" * 56)
    for r in keep:
        roi = 100 * r["net_sol"] / r["sol_deployed"]
        last = "—" if r["hours_since"] is None else (
            f"{r['hours_since']:.0f}h" if r["hours_since"] < 48 else f"{r['hours_since']/24:.0f}d")
        print(f"{r['name'][:24]:<24}{roi:>6.0f}{r['net_sol']:>8.0f}{r['day']:>5}{r['week']:>5}{last:>8}")


if __name__ == "__main__":
    main()
