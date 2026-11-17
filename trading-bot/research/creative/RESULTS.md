# 11 mechanism-first NQ intraday ideas (ideas.py) — 2012-19 choose, 2020-26 check, cost 1.3 bp
None reaches 2012-19 t >= 2. Leads worth a second look:
- Initial-balance breakout (09:30-10:30 range, first break after 10:30, stop IB mid, hold 15:55) on NORMAL-width IB days:
  185/yr, win 42%, RR 1.59, IS +1.8 bp (t 1.36), OOS +4.0 bp (t 1.93), last 2y +1.8 bp, 11/15 years. Narrow-IB days are worse (opposite of the textbook).
- Post-shock day (yesterday's range > 2 ATR): fade the first 30 min, 10:00-12:00: 7.5/yr, win 59%, IS +6.7 bp, OOS +17.8 bp (t 1.5), 11/15 years. Small sample.
- London compression breakout: OOS +7.7 bp (t 1.6) but IS t 0.5, 7/15 years.
Dead: overnight-inventory fade, LETF close, round-number pin, lunch reversal, yen lead, DAX lead, MOC imbalance (costs eat a ~0.3 bp signal).

# THE PLUTO SEQUENCE (invented theory, rules written before the test) — pluto.py
Time in 4s (NY session 06-12 -> 90-min quarters, Q3 -> 22.5-min), price in 4s (yesterday's range halves), three true opens
(00:00 / 07:30 / 09:22), Q2 sweep of Q1, entry 09:45, stop under the manipulation low (min 0.15%), exits 2R / liquidity / 12:00.
18 versions (NQ + S&P): none with 2012-19 t >= 1.2.
- Full sequence NQ: 13/yr, win 30-37%, RR 1.6-2.4, IS +0.07 to +0.20R (t <= 0.8), OOS -0.10 to +0.04R, last 2 years -0.2 to -0.3R.
- Without the micro condition (58/yr): IS ~0R, OOS +0.08-0.09R (t 1.4), 8/15 years.
- S&P: same picture. Verdict: the five-scale alignment does not predict direction.

# THEORY FACTORY (factory.py) — 2.48 million generated time x price theories, three gates + shuffled-day placebo
78 conditions (price vs 9 true opens/mids at 7 times, range quarters, sweeps, flow) x 1-3 combos x 30 entry/exit x 2 orientations.
Gates: 2012-17 t>=3 -> 2018-21 t>=2 same sign -> 2022-26 once.  REAL: 142 survivors; PLACEBO: 2.  139/142 positive in 2022-26.
Almost all survivors are ONE family: "today's early move disagrees with yesterday -> go with today, hold to the close".
Core rule (NQ): at 09:45, if price vs the 09:00 open points the opposite way to yesterday's RTH candle -> trade in today's direction 09:45-15:55.
- 114 trades/yr, win 52.3%, RR 1.25, 2012-17 +10.2 bp (t 3.7), 2018-21 +11.0 (t 2.6), 2022-26 +9.7 (t 1.8), 15/15 years positive.
- Robust to the reference time (00:00 ... 09:20 opens all give +5.6 to +9 bp) -> the 09:00 'true open' is not special.
- + London-mid filter: 53/yr, win 55%, RR 1.32, +15 / +17 / +19 bp, 14/15 years.
- S&P: positive in every period but weak (t 0.5-1.5), 8/15 years -> mostly an NQ effect.
- Risk: no stop, max drawdown ~19% of notional (1 MNQ ~ $9K) — needs a stop/size study before use.
