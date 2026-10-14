# Top strategies (ranked by out-of-sample evidence) — none meets ALL acceptance criteria

| Rank | Strategy | Planned R:R | Realised win/loss ratio | Win % (all, 95 % CI) | Expectancy | Status |
|---|---|---|---|---|---|---|
| 1 | Pre-Open Fade 1:2 (z>2.5, TP 1.0×move, SL 0.5×move) | 1:2 | 1.94 | 50.6 % (40–61) | +0.45 R (CI +0.15 … +0.75) | **PROVISIONAL** — fails 70 % |
| 2 | Pre-Open Fade 1:0.5 (z>2, TP 0.5×move, SL 1.0×move) — research/hunt | 1:0.5 | 0.62 | 76 % | +0.18 R | Validated edge — fails 1:2 |
| 3 | Best evolutionary rule in VAL (long, 14:30–15:00, low rv30, near high) | 1:2 | ≈0.7 (mostly time exits) | VAL 68 % (n=22) | +0.09 R | Rejected — train/val noise, tiny n |

## #1 exact rules (best_strategy/config.json)
- Instrument: MNQ/NQ front month. Data: Databento 1-minute, 2020-01 → 2026-10.
- Signal: move = close(08:59) − open(08:00) ET. z = (move/price) ÷ std of the same window's returns over the previous 20 days. |z| > 2.5.
- Entry: market at the 09:00 open, opposite to the move.
- Target: 1.0 × |move| from entry. Stop: 0.5 × |move|. Time exit 13:00. Stop wins ties.
- Size: risk-based (contracts = risk$ ÷ (stop pts × $2)).
- ≈ 12.6 trades a year.
