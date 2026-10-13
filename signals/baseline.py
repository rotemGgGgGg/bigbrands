"""What does the sender have to beat?

His risk-to-reward sits near 2.5, and it is tempting to read that as needing
only a 29% hit rate, as though 29% were a low bar. It is not a low bar, it is
exactly the bar a coin gets.

For a price with no drift, the chance of touching +34 before -13 is
13/(13+34), which is 28.3%. The breakeven rate for a 2.53 reward-to-risk is
1/(1+2.53), which is 28.3%. The same number, necessarily: reward-to-risk and
the odds of reaching it are two descriptions of one geometry, so a good ratio
says nothing whatever about having an edge.

Which means the only question worth asking about this sender is whether he
beats a random entry on the same instrument with the same levels. This
measures that random entry, on real gold minutes, so there is something to
compare him against before any money moves.

    python3 signals/baseline.py
"""
from __future__ import annotations

import random

from paper import resolve
from prices import from_yahoo, Series


def run(series: Series, risk: float, reward: float, trials: int,
        hold_minutes: int, seed: int = 7) -> dict:
    rng = random.Random(seed)
    bars = series.bars
    # Leave room after each entry for the trade to resolve.
    latest_start = len(bars) - hold_minutes
    if latest_start < 10:
        raise SystemExit("not enough price history for this holding time")

    tally = {"win": 0, "loss": 0, "ambiguous": 0, "open": 0}
    for _ in range(trials):
        i = rng.randrange(0, latest_start)
        entry = (bars[i].high + bars[i].low) / 2
        side = rng.choice(("buy", "sell"))
        stop = entry - risk if side == "buy" else entry + risk
        target = entry + reward if side == "buy" else entry - reward
        window = Series(bars[i:i + hold_minutes], series.source, series.symbol)
        r = resolve(side, entry, stop, target, bars[i].ts, window)
        tally[r.outcome] += 1
    return tally


def main() -> None:
    series = from_yahoo(range_="7d")
    print(f"{series.symbol}: {len(series.bars)} minute bars over 7 days")
    lo = min(b.low for b in series.bars)
    hi = max(b.high for b in series.bars)
    print(f"range over the week: {lo:.2f} - {hi:.2f}  ({hi - lo:.2f} wide)\n")

    risk, reward = 13.48, 34.15      # his actual numbers
    rr = reward / risk
    breakeven = 1 / (1 + rr)
    print(f"his levels: risk {risk}, reward {reward}, R:R {rr:.2f}")
    print(f"breakeven win rate: {100 * breakeven:.1f}%\n")

    print(f"{'hold':>8}{'settled':>9}{'win rate':>10}{'ambiguous':>11}{'unresolved':>12}")
    for hold in (60, 240, 480, 1440):
        t = run(series, risk, reward, trials=400, hold_minutes=hold)
        settled = t["win"] + t["loss"]
        rate = f"{100 * t['win'] / settled:.1f}%" if settled else "-"
        print(f"{str(hold) + 'm':>8}{settled:>9}{rate:>10}"
              f"{t['ambiguous']:>11}{t['open']:>12}")

    print("\nA random entry landing near the breakeven rate is the point: the "
          "\nratio is not an edge. Whatever the sender scores has to beat this "
          "\nrow, and the broker's spread comes off his side only.")


if __name__ == "__main__":
    main()
