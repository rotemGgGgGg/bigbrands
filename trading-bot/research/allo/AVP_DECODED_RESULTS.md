# AVP Zones (decoded) - verdict, Nov 28 2026

## What the indicator is
- Blue zone = previous session close (17:00 NY) +/- ~45 pt (6/6 days within 6 pt of his blue zones).
- Red/green (RZ/SZ) = previous session VWAP +/- k*S, k = 1..3, S ~ mean of the last 3 sessions' VWAP sigma (cv 0.14).
- Signal (his video): price on one side, a candle pops into the zone, an opposing candle closes back out -> enter at the
  close; stop = far side + 2 ticks; target fixed R / next zone; flip after a stop; one trade per zone; flat 16:00.

## Reconstruction check (avp_bt.py, Oct 1 - Nov 20 2026)
Our engine fires on the same days and sides as his chart on ~18 of 21 trade days (Oct 9, 21, 23, 26, 27, 28; Nov 2, 3,
10, 12, 18, 19, 20 ...), usually 5-15 minutes apart (zone height / settlement vs last-trade close).

## History test (Databento NQ.v.0 1-minute, 2011-2026, 1 pt cost, settings chosen on 2011-19 only)
| | n | avg R | t | win % |
|---|---|---|---|---|
| 2011-2019 (best of 72 settings: H=45, 3R, flip) | 600 | +0.019 | 1.02 | 53.3 |
| 2020-2026 (judged once) | 1401 | -0.004 | -0.16 | 44.9 |
| Placebo 2020-26, random zones (40 runs) | | mean -0.010, 95th pct +0.076 | | p = 0.51 |
Years 2024 / 2025 / 2026: -0.058 / -0.083 / -0.016 R. None of the top-5 in-sample settings is positive out of sample
beyond +0.014R (t 0.45).

## Verdict
No edge. The decoded rule is a rejection at yesterday's close; it behaves like random zones (p = 0.51) and has been
negative for the last three years. His chart table (+7.49R on 24 trades) is one short window; the next window showed
-3.03R on 6 trades. Do not renew (access ends Dec 5, 2026).
