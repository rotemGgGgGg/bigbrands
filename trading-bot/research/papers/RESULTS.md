# Classic-paper strategies — 127 strategies, 6 levels

Data: HistData free 1-minute Nasdaq-100 CFD (NSXUSD), 2012-01 → 2026-10, RTH 09:30-16:00 NY (timestamps checked against the
08:30 / 09:30 / 10:00 volatility spikes). Published rules and default parameters, nothing tuned. Costs 2.25 pt × price/17000
per round trip. Daily signals are executed at the next open. Coin flips: 500 draws each of random timing (circular shift or
random days) and random direction, and a strategy must beat both.

| Level | Test | Passed |
|---|---|---|
| L1 | 2015-2017 net > 0, ≥15 trades | 49 / 127 |
| L2 | 2012-2017 net > 0 + both coin flips p<0.05 | 8 |
| L3 | 2018-2020 unseen, net > 0 | 5 |
| L4 | 2021-2023 at 2× costs + coin flips 2012-2023 | 2 |
| L5 | Bonferroni (p < 0.05/127) + lookbacks ×0.75 / ×1.25 | 1 |
| L6 | holdout 2024-2026, one look | **1** |

Survivor: **Connors %b (Connors & Alvarez 2009)**: long when the close is above SMA200 and %b(5,1) < 0.2 for 3 days; exit when %b > 0.8.
The trade is executed at the next open, so it is causal (0/30 mismatches in the future-scramble check).
- 115 trades in 14.8 years (7.8 per year), win 74.8%, R:R 0.74, average hold 3.4 days, about $124 per trade with 1 MNQ.
- Losing years: 2016 and 2019. It is long-only in a market that rose 12×.
- Lucid 50K: with 1 MNQ it takes ~100–1,600 trading days to fund, and starting in 2022–2025 it is blown.
- Conclusion: statistically real but too small and slow to run an eval/prop account on its own.

Bug caught during the audit: the Camarilla H3/L3 fades first "passed" every level because a stop that the open had already gapped
through was exited at the stop level instead of the fill. After the fix in engine.exits, both are dead.
Untestable here (the data has no volume): OBV, MFI, VWAP, Chaikin, Force index, pocket pivot, and pre-FOMC drift (no FOMC calendar).
Full table: levels.csv. Code: pdata.py, engine.py, strats.py, run.py, survivor.py, audit_cam.py.
