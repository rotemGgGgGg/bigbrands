# LAYERS: 13,271,040 multi-timeframe strategies (NQ 1-min, 2012-2026, cost 1 pt)
HTF gap (D/4H/1H) -> touch (near/50%/far) -> react or invert -> 15m confirmation (8 kinds) -> 1m entry (4) -> stop (4) -> target (6)
-> 960 context filters (gap size, age, session, trend, day state). Placebo: same factory, every zone moved 1-3 widths at random.

| | real | placebo |
|---|---|---|
| strategies | 13,271,040 | 13,271,040 |
| pass 2012-17 (t>=3) and 2018-21 (t>=2) | **17** | **22** |
| survivors positive in 2022-26 | 1 of 17 | 6 of 22 |
| unfiltered configs with t>=3 | 0 | 0 |

Verdict: no tradeable strategy. The factory finds fewer winners than the random twin, and the winners fail out-of-sample.

One real effect (family level, nothing selected): daily gaps, react mode, all 2,304 configs:
real avg R -0.012 / +0.034 / +0.050 (2012-17 / 2018-21 / 2022-26) vs placebo -0.159 / -0.024 / -0.081.
Real daily gaps beat random levels by ~0.1R in every period, but on their own they stay near zero after costs.
4H and 1H gaps are no better than random levels.
