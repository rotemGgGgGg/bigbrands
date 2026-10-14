# NA-FVG Scalp — final product

**Idea:** take a signal with a real directional edge (the day breaks out of its normal noise band — intraday momentum),
enter on the first pullback into a 1-minute Fair Value Gap in that direction, and shape the payoff: a tiny target
(0.15 × typical daily move ≈ 19 NQ points) and a wide stop (2 × daily move). The edge keeps the expectancy positive;
the payoff shape turns it into a very high win rate.

**Backtest (MNQ 1-min, 2020-01 → 2026-10, $2.50 costs, conservative fills: entry and target need a 1-tick trade-through):**
| | Value |
|---|---|
| Trades | 812 (≈10 / month) |
| Win rate | **88.3 %** |
| Avg win / avg loss | +$39 / −$214 per MNQ |
| Avg per trade | +$9.3 per MNQ |
| Profit factor | 1.37 |
| 2020–23 / 2024–26 | +$5.3 / +$15.4 per trade |
| Longest win streak / loss streak | 49 / 2 |
| Max drawdown | −$1,579 per MNQ |
Neighbourhood (target 0.10–0.20, stop 1.5–3.0): every combination positive in both periods, 84–92 % wins.
Files: signals.py (grid of 6 edge signals × payoff shapes), deep.py, conservative.py, *_results.txt.
Pine: trading-bot/pine/na_fvg_scalp.pine (1-minute chart).
