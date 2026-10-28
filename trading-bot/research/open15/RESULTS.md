# Opening-window search (first 1-15 minutes after 09:30), 12.4M variants

Grid:
- Opening window K: 1 / 2 / 3 / 5 / 10 / 15 minutes.
- Anchor range: opening range, previous day, pre-market, gap.
- Entry level: 15 Fib levels.
- Order type: limit or stop. Side: long or short.
- Stop: 8 values. Target: 8 values. Exit time: 5 values.
- Filters: 27 combinations.

Data: HistData NSXUSD 1-minute (Nasdaq-100 CFD), 2012-01 to 2026-10. Costs are 2.25 pt × price/17000. Fills are strict (see o15.py).

- Variants with at least 150 trades in 2012-2019: 9,556,928.
- Luck bar for that many tries: t = 5.67. The best in-sample t was 5.65, so **0 variants pass the strict path**.
- Variants with t ≥ 3: 6,462. Pure noise would produce about 12,900, so the search as a whole finds nothing beyond chance.
- Soft path (t ≥ 3 and ≥ 6 of 8 positive train years): 5,850. Of those, 265 pass 2020-2023 validation (> 0, t ≥ 2), and 201 of the 265 are positive in the holdout.

Finalists: the top 3 families by validation t, chosen before the holdout was looked at.

| # | rule | trades/yr | win | R:R | coin flips | holdout 2024-26 |
|---|---|---|---|---|---|---|
| 1 | gap-up day, red first minute, opening range larger than its median → sell stop at the 0.618 of the gap, no stop, target 0.5 × gap, exit 11:00 | 25 | 78% | 0.60 | p = 0.002 / 0.002 | + (2025 −) |
| 2 | 15-min opening range breakout at 1.272 long, no stop | 22 | 65% | 0.67 | 0.002 / 0.002 | **− (2025, 2026 heavy losses)** |
| 3 | gap-up day, small 5-min opening range → buy stop at the 2.618 extension of the opening range, stop 1 × range, target 3 × range, exit at the close | 19 | 44% | 2.95 | 0.002 / 0.002 | + every year |

Notes on #3:
- 13 of 15 years are positive, and it stays positive at 2× costs.
- 91 of 108 parameter neighbours are positive in train, validation and holdout.
- It did NOT pass the multiple-testing luck bar (train t 3.3 vs 5.67), so it is a candidate, not a proof.
