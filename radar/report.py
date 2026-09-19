"""Morning report: what each alert did afterwards, and what the data says
about where the thresholds should sit.

Run: python report.py
"""
import json
from collections import defaultdict

import store


def _pct(before, after):
    if not before or not after:
        return None
    return (after / before - 1) * 100


def _fmt_pct(value):
    if value is None:
        return "   —  "
    return f"{value:+7.0f}%"


def _fmt_money(value):
    if not value:
        return "    —"
    if value >= 1_000_000:
        return f"${value/1_000_000:.1f}M"
    return f"${value/1000:.0f}k"


def load_rows(conn):
    outcomes = defaultdict(dict)
    for row in conn.execute("SELECT * FROM outcomes"):
        outcomes[row["alert_id"]][row["label"]] = dict(row)

    rows = []
    for alert in conn.execute("SELECT * FROM alerts ORDER BY ts"):
        payload = json.loads(alert["payload"])
        marks = outcomes.get(alert["id"], {})
        entry = marks.get("0m", {})
        base = entry.get("price_usd")
        rows.append(
            {
                "id": alert["id"],
                "mint": alert["mint"],
                "score": alert["score"],
                "wallets": alert["wallet_count"],
                "span": int(payload.get("span_sec", 0)),
                "sol": payload.get("total_sol"),
                "entry_mcap": entry.get("mcap_usd"),
                "m15": _pct(base, (marks.get("15m") or {}).get("price_usd")),
                "h1": _pct(base, (marks.get("1h") or {}).get("price_usd")),
                "h24": _pct(base, (marks.get("24h") or {}).get("price_usd")),
                "has_base": base is not None,
            }
        )
    return rows


def main():
    conn = store.Store().conn
    rows = load_rows(conn)
    if not rows:
        print("no alerts recorded yet")
        return

    print(f"\n{len(rows)} alerts recorded\n")
    print(f"{'#':>3} {'score':>5} {'w':>2} {'span':>5} {'SOL':>6} {'entry':>7} "
          f"{'+15m':>8} {'+1h':>8} {'+24h':>8}")
    print("-" * 66)
    for row in rows:
        print(
            f"{row['id']:>3} {row['score']:>5} {row['wallets']:>2} "
            f"{row['span']:>4}s {row['sol']:>6.1f} {_fmt_money(row['entry_mcap']):>7} "
            f"{_fmt_pct(row['m15'])} {_fmt_pct(row['h1'])} {_fmt_pct(row['h24'])}"
        )

    measurable = [r for r in rows if r["h1"] is not None]
    print(f"\n{len(measurable)} of {len(rows)} alerts have a measurable 1h outcome.")
    if not measurable:
        print("Nothing to calibrate on yet — most alerted tokens had no "
              "DexScreener pair at alert time (pre-bonding).")
        return

    def summarise(label, subset):
        if not subset:
            print(f"  {label:<18} no alerts")
            return
        wins = [r for r in subset if r["h1"] > 0]
        median = sorted(r["h1"] for r in subset)[len(subset) // 2]
        print(f"  {label:<18} n={len(subset):>2}  up after 1h: "
              f"{len(wins)}/{len(subset)}  median {median:+.0f}%")

    print("\nBy score band:")
    summarise("50-64", [r for r in measurable if r["score"] < 65])
    summarise("65-79", [r for r in measurable if 65 <= r["score"] < 80])
    summarise("80+", [r for r in measurable if r["score"] >= 80])

    print("\nBy wallet count:")
    summarise("3 wallets", [r for r in measurable if r["wallets"] == 3])
    summarise("4 wallets", [r for r in measurable if r["wallets"] == 4])
    summarise("5+ wallets", [r for r in measurable if r["wallets"] >= 5])
    print()


if __name__ == "__main__":
    main()
