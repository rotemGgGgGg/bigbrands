# GapFB bot — reconstructed from its Discord alerts and backtested

## Rules (read off the alerts, verified on Databento MNQ July 2026)
- Gap = 09:30 open vs prior 15:59 close; qualifies at |gap| ≥ ~0.3 % (alerts 0.33 %+, no alert on −0.26 % / −0.02 %).
  Our gap numbers match the alerts (0.97 vs 0.98, 1.52 vs 1.52, −0.75, −1.52, 1.09, −0.86, 1.98, 1.23 %).
- OR = 09:30–09:34 high/low (matches to 1–2 ticks). Buy stop at OR high, sell stop at OR low.
- Stop = 2 × ATR(14) of 1-minute bars at the fill, target = 2 × stop (2:1). Up to 2 trades a day, both sides re-armed.
- Replication check: NQ trade sides for 7/17–7/30 match every posted alert (e.g. 7/20 long→short, 7/21 short→long,
  7/22 long,long, 7/23 long,long, 7/27 short,short, 7/28 short,short, 7/30 long,long).

## Result (costs 2.25 pt round trip) — no edge
| period | trades/yr | win | avg R |
|---|---|---|---|
| MNQ 2020–23 | ~324 | 34.1 % | −0.04 |
| MNQ 2024–26 | ~292 | 34.0 % | −0.06 |
| NSX CFD 2012–19 | ~245 | 35.4 % | −0.05 |
34 % at 2:1 is the random-entry barrier (1/3); before costs ≈ 0 R. Threshold 0.5 %, entry cut-off 12:00, time exit 12:00,
trade #1 / #2 only: all ≈ −0.03…−0.10 R. `python3 gapfb.py` reproduces everything.

## The author's real variant (from his YouTube video): stop only, NO take-profit, time exit
Data: the user's Databento NQ 1-minute file 2010-06 → 2026-07 (front month by prior-session volume; matches our MNQ
to a median 0.25 pt over 2.3 M overlapping minutes) for 2010–19, Databento MNQ for 2020–26. `notp.py`, `notp_check.py`,
`notp_years.py`.

Same entries (gap ≥ 0.3 %, 5-min OR stop entries), stop 3 × ATR(14, 1-min) at the fill, no target, exit 15:55, 1 trade a day:
| period | trades/yr | win | R:R (avg win / avg loss) | avg R |
|---|---|---|---|---|
| 2010–19 | ~130 | 24.2 % | 3.70 | +0.14 |
| 2020–23 | ~160 | 25.3 % | 3.67 | +0.19 |
| 2024–26 | ~150 | 27.0 % | 3.00 | +0.08 |
- Robust: gap ≥ 0.2 / 0.3 / 0.5 % all positive in every period; exit 12:00 also positive (31 % win, 1:2.5).
- Placebo: the same trade on NON-gap days (|gap| < 0.3 %) is negative in 2010–19 and 2020–23 → the gap filter carries the edge.
- 15 of 17 calendar years positive (2015 −31 R, 2025 −9 R). Total +336 R over 2,287 trades.
- Risk: max drawdown 50.7 R, longest losing streak 31 trades. On a $2K trailing-drawdown eval that means ≤ ~$40 risk per trade,
  below 1 MNQ at a 3×ATR stop (~60 NQ pts ≈ $120) — fine for a personal account sized for 50 R, hard for a prop eval.

## Improvement search (gapfb2*.py) — strict funnel
7,776 configs chosen on TRAIN 2010–19 only → top 300 by t → VALIDATE 2020–23 (252 pass t > 1.5) → TEST 2024–26 opened once
for 3 configs fixed in advance. Dominant family: **15-minute OR, trade only in the gap's direction, stop 2×ATR(1m),
entries until 10:30, exit 15:55, gap ≥ 0.3 %, 1 trade a day.**
| config | 2010–19 | 2020–23 | 2024–26 (TEST) | all 2010–26 |
|---|---|---|---|---|
| A simple | 26.8 % win, 1:3.95, +0.35 R | 28.5 %, 1:3.86, +0.40 R | 24.6 %, 1:3.44, +0.10 R (t 0.7) | +431 R, DD 38 R, streak 15, 15/17 yrs |
| B + BE at 2R | 24.3 %, 1:4.87, +0.38 R | 23.9 %, 1:5.13, +0.39 R | 19.4 %, 1:4.42, +0.04 R | +433 R, DD 50 R, 14/17 yrs |
| C + 5×ATR trail | 33.5 %, 1:2.94, +0.32 R | 32.8 %, 1:3.09, +0.32 R | 27.8 %, 1:3.07, +0.13 R (t 0.9) | +385 R, DD 34 R, streak 12, 14/17 yrs |
~80–90 trades a year. TEST is still positive but much weaker and not significant on its own; 2025 and 2026 YTD negative.

## Pre-entry filters on config C (gapfb3.py; judged on 2010–19 and 2020–23 separately)
Helped in both: yesterday's candle AGAINST the gap (+0.54 / +0.44 R vs +0.08 / +0.17 R) and first 15 min closing in the gap
direction (+0.35 / +0.41 vs +0.25 / +0.14). Noisy / inconsistent: gap size in σ, outside yesterday's range, 20-day trend,
OR location/width, weekday, VIX.
TEST 2024–26 (opened once for C + yesterday-against): +0.12 R vs the complement +0.22 R → the filter does NOT hold in TEST.
Over 2010–26 it halves drawdown (21.6 R vs 33.8 R, 16/17 years positive) but its TEST evidence is negative → not adopted.

## Other markets (gapfb4_multi.py) — NQ-specific
GapFB-C on SPX CFD: +0.07 / +0.26 / −0.09 R; gold: +0.10 / +0.08 / −0.05 R; NQ: +0.34 / +0.32 / +0.22 R (2012–25).
Adding them triples drawdown (NQ 19.8 R → NQ+SPX+GOLD 66.9 R). Trade NQ only.

## Lucid 50K eval (gapfb5_eval.py; attempts started every 5th day 2020–26, EOD trailing $2K, consistency 50 %)
| risk/trade | pass % | median trading days to pass |
|---|---|---|
| $100 (1 MNQ) | 75 % | 295 |
| $200 | 54 % | 95 |
| $300 | 46 % | 59 |
| $400 | 42 % | 46 |
| $600 | 30 % | 41 |
Slow: ~0.4 trades a day and 25–33 % wins → long flat stretches. Not faster than the earlier eval-engine policies.

## Execution sensitivity (gapfb6_latency.py)
2024–26: on time +0.13 R → 1 min late −0.01 R, 2 min +0.03 R; +2 pt extra slippage +0.07 R, +4 pt +0.01 R.
→ Must be a RESTING stop order placed at 09:45 at the OR level (as the author does), not a market order after a bar-close alert.

## More families (zones.py, zones_fade.py, day2.py, addon.py)
- Overnight / prior-day high-low breakouts at the open: negative in every period (ON-HL −0.27/−0.23/−0.46 R); fading them also
  negative → churn zone, both sides lose.
- Day-2 continuation after a GapFB trade: negative 2010–19 → fail.
- **Add-on (pyramid):** after the base trade reaches +1 R, add a 2nd unit on the first 1-min close back to the 20-EMA (own 2×ATR
  stop, shares the 5×ATR trail). Add-on alone: +0.49 / +0.21 / +0.34 R (2010–19 / 2020–23 / 2024–26), positive for arm at
  +1/+2/+3 R and EMA 10/20/50. Combined 2010–26: +665 R vs +385 R, max DD 55 R vs 34 R, return/DD 12.2 vs 11.4.

## Exit and entry refinements (exits.py, entries.py)
- Exits: base 5×ATR trail is best; trail 4/6, tighten after 14:00 / +3 R, partial ½ at +2 R, BE at +1 R all ≤ base in TEST.
- Entries: buffers beyond the OR and later cut-offs hurt. **OR width filter helps monotonically**: skip days whose 15-min OR is
  narrower than w×ATR(1m). w = 3 / 3.5 / 4 / 5 → TEST 2024–26 +0.17 / +0.22 / +0.37 / +0.47 R (train/val also ≥ base).
  w = 4: 342 / 156 / 104 trades, +0.35 / +0.49 / +0.37 R, ~37 trades a year.
