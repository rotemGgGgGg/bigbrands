# Multi-market portfolio — results (8 markets, FTSE still downloading)

Same honest rule as combo15: eligible = alpha t >= 1.0 and >= 5/8 positive-alpha years on 2012-19; take ALL eligible, equal risk, beta-hedged. OOS = 2020-2026-10.
Data: Dukascopy 1-min (DAX, gold, USDJPY, Nikkei, EURUSD, WTI) + HistData (NQ, SPX). 178 strategies (127 papers + 51 old-web rules) per market.

1297 strategy x market series -> 145 eligible.

| market | eligible | IS Sharpe | OOS 2020-26 | 2020-22 | 2023-26 |
|---|---|---|---|---|---|
| NQ (NSXUSD) | 26 | 1.42 | **0.80** | 0.69 | 0.94 |
| S&P (SPXUSD) | 20 | 1.29 | **0.59** | 0.30 | 0.93 |
| USDJPY | 16 | 1.19 | 0.34 | 0.98 | -0.20 |
| Nikkei | 31 | 1.71 | 0.28 | -0.01 | 0.48 |
| Gold | 12 | 1.09 | 0.22 | -0.34 | 0.60 |
| WTI | 17 | 0.86 | 0.05 | 0.36 | -0.34 |
| DAX | 10 | 1.33 | -0.01 | -0.30 | 0.31 |
| EURUSD | 13 | 1.24 | -0.27 | -0.51 | -0.05 |

All 145 together: IS Sharpe 3.19 -> OOS 0.66 / 0.83 (t 1.95). Worse than NQ-only combo15 (OOS 0.97, t 2.43).
Market sleeves are uncorrelated OOS (|corr| mostly < 0.1) — the diversification is real, the edges outside US indices mostly are not.
Prop 50K: 5% vol -> 39% payout / 55% fail; 10% -> 29% / 71%.

Conclusion: strategies born on US index data do not transfer. Non-US markets need their own native ideas
(carry/FX session effects, commodity term structure, Asian-session index effects), not ported US intraday rules.
