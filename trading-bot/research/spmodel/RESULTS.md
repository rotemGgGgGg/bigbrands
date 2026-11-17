# SP Model v8 (rules unchanged) — 2012-2026 backtest on Nasdaq-100 1-min (HistData CFD), 5-min bars, R before costs
Volume: CFD has none -> time-at-price (TPO) profile as proxy for the futures volume profile. Holidays excluded only 2020+.

| | A London 00:00-06:00 (spec) | B London 02:00-09:30 (user's box) |
|---|---|---|
| trades / yr | 172 | 167 |
| win rate | 46.1% | 46.5% |
| RR (avg win / avg loss) | 1.10 | 1.08 |
| avg R / trade | -0.03 (t -1.4) | -0.03 (t -1.6) |
| total R 2012-26 | -73.9 | -84.1 |
| 2012-19 / 2020-26 avg R | -0.04 / -0.02 | -0.07 / +0.01 |
| max drawdown | -122 R | -124 R |
| positive years | 5/15 | 4/15 |
| best scenario | S2 +0.01R (1061 trades) | S2 +0.03R (609 trades, t 0.7) |
| prop 50K, $250 risk, 2020-26 | 5% payout / 82% fail | 20% payout / 76% fail |
Neither window has an edge; breakeven win rate 46.5% (0.5 entries) / 50% (0.588). Costs (~0.02-0.05 R/trade) would make both more negative.

## What to change (improve.py: diagnose + 72 re-simulated variants, choose on 2012-19, check 2020-26)
Consistent in BOTH periods:
- Shorts lose (-0.07R IS and OOS); longs ~0 to +0.02R.  S1 loses (-0.08 / -0.07R).  S3 slightly negative.
- 09:30-10:00 and 13:00+ entries are the weakest.
Best variants (none reaches 2012-19 t >= 2):
- S2 only + with daily trend (NQ vs 50-day avg), brackets unchanged: 32 trades/yr, win 52%, RR 1.07, IS +0.07R (t 1.1), OOS +0.08R (t 1.1), 9/15 yrs.
- All scenarios, target -0.27 extension + stop at fib 1.0: 172/yr, win 42%, RR 1.44, IS +0.03R, OOS +0.03R (t 0.9), 11/15 yrs.
Verdict: changes move it from about -0.03R to about +0.05R per trade; still not statistically proven and thin after costs.
