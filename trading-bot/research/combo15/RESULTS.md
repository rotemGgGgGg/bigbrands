# combo15 - many small strategies together (NQ / NSXUSD 1-min, 2012 - 2026-10)

Pool: 192 strategies (127 classic papers, 59 pre-2002 internet rules, 6 rebuilt survivors / practitioner edges incl. Turnaround Tuesday).
Selection on 2012-2019 only; 2020-2022 validation; 2023-2026 final. Costs 2.25 pt x price/17000 per round trip.

| attempt | result |
|---|---|
| Greedy pick of 15 by in-sample Sharpe (combo.py) | in-sample Sharpe 2.31, validation 0.45: beats only 4% of random 15-portfolios -> the picking is luck; portfolio is ~1 contract long NQ (beta 0.8-1.06) |
| Alpha-ranked, corr < 0.3, top 15 (combo2.py) | again beats only 2% of random portfolios in validation |
| **No picking: ALL 24 strategies with alpha t >= 1 and >= 5/8 positive alpha years on 2012-19, equal risk, beta-hedged (combo3.py)** | **2020-26 hedged Sharpe 0.97, t = 2.43; beats 100% of 300 placebo portfolios (24 random strategies, median 0.19, 95th pct 0.68); 15/15 years positive** |

All-24 portfolio, equal risk (30 pt daily stdev per strategy), beta-hedged:
- 2012-19 Sharpe 1.35, 2020-22 0.81, 2023-26 1.10; winning days 39%, average win/loss 1.9-2.1.

Prop 50K simulation (target $3K, $2K EOD trailing drawdown, 50% consistency, then the first $1.5K payout; starts every 5th day 2020-26):

| sizing | payout | fail | median days to pass / payout |
|---|---|---|---|
| x0.05 | 58% (rest still open) | 0% | 426 / 651 |
| x0.10 | 79% | 20% | 216 / 338 |
| x0.20 | 38% | 62% | 81 / 110 |
| 1 MNQ per strategy | 15% | 85% | (too big: worst day -$5.1K, max DD -$26K) |

Caveats: the 24 are not 24 independent bets. 7 are opening-range-breakout variants, 4 are OOPS variants and several are long calendar/overnight holds,
so the real count is about 8-10 families. Equal-risk weights are fractions of a micro: tradeable on an MT5 CFD with 0.01 lots, not with whole MNQ.
