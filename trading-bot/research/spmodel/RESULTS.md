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

## New strategy from the autopsy: London Break & Retest (lbr.py) — failed
Trend-side 5-min close beyond the London level 09:30-11/12:00; entry on retest or at the break; stop 0.25/0.5 London range; 2R or 15:55.
32 variants (16 x trend on/off), choose 2012-19, check 2020-26 and S&P.
- Nothing reaches 2012-19 t >= 2. Best: breakout entry, tight stop, hold to 15:55, NO trend filter: 220/yr, win 29%, RR 2.6, IS +0.065R (t 1.2), OOS +0.04R (t 0.8).
- The trend filter made every variant worse (mean IS -0.15R vs -0.08R).
- Retest entries are the worst (down to -0.27R): when price comes back to the broken London level, the break usually fails.
- Pre-chosen pick (best IS with trend) on S&P: -0.07R, 2020-26 -0.08R. Last 2 years NQ +0.01R.

## 1-minute re-resolution (resolve1m.py) - ~30% of trades open and close inside one 5-minute bar
| | 5-min sim | 1-min, target allowed in fill minute (optimistic) | 1-min, stop only in fill minute (conservative) |
|---|---|---|---|
| A 00-06, last 3y | 49.9%, +0.041R | 57.4%, +0.202R | 50.5%, +0.058R (t 1.2) |
| B 02-09:30, last 3y | 49.4%, +0.021R | 59.5%, +0.246R | 52.5%, +0.102R (t 2.1) |
| B 02-09:30, 2020-26 | 48.9%, +0.013R | | 51.5%, +0.074R (t 2.3) |
| B 02-09:30, 2012-19 | 44.7%, -0.069R | | 46.3%, -0.034R |
Truth sits between the two 1-minute columns. Nowhere near 69-74% win rate with these brackets (target ~1.1R).
