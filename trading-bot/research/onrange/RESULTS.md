# Overnight-range quarters claim — results

Claim: at the 09:30 open, if price is in the half of the overnight (18:00-09:29) range near the low, RTH takes the ON low 75.6%;
near the high, takes the ON high 81%.

## 1. Replication (NQ CFD 2012-2026)
Lower half takes ON low **76.1%**, upper half takes ON high **79.3%** — the numbers are real.
But a level at the **same distance on the other side of the open** is touched 80.9% / 78.0%. S&P identical (74.6 vs 78.4, 78.1 vs 77.8).
DAX, gold, USDJPY, Nikkei, EURUSD, WTI: same — ON level and mirror level within a few points.
=> The % is just "a nearby level gets touched". No direction in it.

## 2. As a trade (trades.py, 72 variants: zone x toward/away x target 50/100% x stop 0.5/1/2R, NQ+SPX, net costs)
0 of 72 positive in 2012-19 with t > 1. Best in-sample (t 0.61) -> OOS t -1.67. "Toward the level" is consistently worse than "away".

## 3. As a filter on our existing 145 eligible strategy x market series (filt.py, placebo.py, sub.py)
Rule fixed on 2012-19: for each strategy keep only the ON-zones (quarters) where its 2012-19 mean P&L > 0.
- Single strategies: improved OOS in 68/145 (coin flip).
- Whole portfolio (all 8 markets): OOS Sharpe 0.90 -> 1.25; 2020-22 0.69 -> 1.13; 2023-26 1.12 -> 1.41; 6/7 OOS years better.
  Shuffled-zone placebo (200 runs): median 0.86, 95th 1.07 -> real beats 100%.
- Per market: NQ 0.82->0.88 (placebo beats 72%, noise), SPX worse, gold/EURUSD worse;
  gains come from DAX 0.10->0.59, WTI 0.05->0.48, Nikkei 0.41->0.61 (each beats 96-100% of placebo).
Caveat: 8 markets tested; the per-market winners are post-hoc. The all-market portfolio test was the pre-specified one.
