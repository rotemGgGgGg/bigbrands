# DFR — Asia 21:00–00:00 NY range, Fibonacci extensions −1 / −2 / −2.5 / −4
Data: Databento MNQ 1-minute 24h, 2020-01 → 2026-10 (1,656 sessions). Median Asia range 22.6 pts.
Tested (dfr.py → 537,222 simulated trades; analyze.py → 3,582 configurations): fade vs break, upper vs lower, 4 levels,
5 windows (London, pre-market, NY AM, NY PM, all day), 3 stops, 5 targets, 3 range-size filters. TRAIN 2020–23, TEST 2024–26.

Result: no edge.
- Only 9 % of configurations are positive in TRAIN; none has t > 2.5; average −0.27 R (break) / −0.24 R (fade) after costs.
- Even with ZERO costs the best rows are ≈ 0 R (e.g. fade at −2: 49.7 % wins at 1:1, +0.002 R).
- Why it *looks* like it works: the levels are reached often (−1: ~68 % of days, −2: ~49 %, −2.5: ~41 %, −4: ~25 %), so price
  frequently "respects" a level on the chart — but stopping there or breaking through are both a coin flip.
