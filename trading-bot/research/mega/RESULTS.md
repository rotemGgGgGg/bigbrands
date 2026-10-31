# Mega search (NQ only, NSXUSD 1-min 2012-2026-10)
Theories: 56 time anchors x 21 Fib levels x 4 triggers (limit / stop / close-through / sweep-reclaim) x 4 windows x 2 sides x 27 contexts
= 1,016,064 theories; x 60 exit plans = 60,963,840 variants (49,533,660 with >= 100 train trades).
Selection 2012-2018, validation 2019-2022, final 2023-2026-10 looked at once. Costs 2.25 pt x price/17000.

| stage | count |
|---|---|
| train t >= 2.5 | 33,479 (pure noise would give ~307k) |
| train t >= 4 and >= 5/7 years positive | 400 |
| strict luck bar t >= 5.95 | 6 -> 0 pass validation |
| validation 2019-22 (t >= 2.5, 3/4 years) | 4 |
| 2x costs + neighbours + family de-dup | 3 |
| **final 2023-2026: net > 0 and coin flips p < 0.05** | **0** |

All 3 finalists are the same idea (short break of the 09:31/09:32 candle extension on wild days with prev-day and overnight down),
win 62-71%, R:R ~0.5 (stop 4u, target 2u), ~15 trades/yr; all lost in 2026 (-$1.1k to -$1.9k per MNQ) and are net negative
on the final period; coin flip p = 0.35-0.74. Verdict: nothing validated. See final.csv.
