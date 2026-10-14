# Correlated FVG (LuxAlgo FVG + ES/YM correlation + Quarterly Theory) — full test

Data: Yahoo NQ/ES/YM 1h (2024-05 → 2026-10) and 5m (~70 days); 15m/4h resampled. Survivors re-checked on Databento NQ 2020-01 → 2024-05.
Grid: 4 timeframes × 256 entry/stop/R:R/after-quarter/alive configs × 10,800 filter combos (correlation, quarter, killzone, bias, size,
displacement, direction) = **11,059,200 combinations**. Costs 2.25 pt per round trip, conservative fills.

Two look-ahead bugs found in my own simulator and fixed before any conclusion:
1. A bar that touched the entry and closed through the gap was cancelled instead of filled (made "far-edge" entries look profitable).
2. The "ES/YM gap still alive" check used the close of the entry bar itself (made correlation look 72/72 better).

Results after fixes:
- Planned R:R ≥ 1:2 with ≥ 70 % wins in TEST: **0** on every timeframe.
- At 1:1, real filters beat shuffled-label nulls on 1h (33 vs 0–8) and 4h (25 vs 0–4); not on 5m/15m.
- The two best (1h Tuesday large gap long; 4h week-4 displacement gap) **fail on unseen 2020–2024 NQ**: 49.5 % / 49.6 % wins, −0.04 R / −0.03 R.
- "Alive" correlation improves expectancy in 54/72 TEST configs (vs 61/72 TRAIN) — a mild, real-looking effect, but never enough to make the trade positive on its own.
Verdict: useful context (as its author says), not a high-win-rate strategy.
