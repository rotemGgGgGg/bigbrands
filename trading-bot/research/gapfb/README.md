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

## Final candidate (final.py) — 2010–26, NQ
| version | trades/yr | win (per day) | R:R | R per day 2010–19 / 2020–23 / 2024–26 | total | max DD | years + |
|---|---|---|---|---|---|---|---|
| C base | ~85 | 28–34 % | 1:3.0 | +0.32 / +0.32 / +0.13 | +385 R | 34 R | 14/17 |
| C + OR ≥ 3.5 ATR | ~53 | 29–35 % | 1:3.2 | +0.30 / +0.44 / +0.22 | +278 R | 29 R | 15/17 |
| C + OR ≥ 3.5 ATR + add-on | ~53 | 22–29 % | 1:4.5–4.9 | +0.54 / +0.61 / +0.40 | +458 R | 49 R | 14/17 |
| C + OR ≥ 4 ATR | ~38 | 30–36 % | 1:3.3 | +0.35 / +0.49 / +0.37 | +234 R | 27 R | 15/17 |
| C + OR ≥ 4 ATR + add-on | ~38 | 25–31 % | 1:4.6 | +0.61 / +0.72 / +0.65 | +387 R | 46 R | 13/17 |
(R = units of the base trade's initial risk; with the add-on a day can risk up to 2 R.)

## Quality score (clf.py → simple rule) — best and most stable result
Logistic regression on 09:45 features (train 2010–19) keeps the top 50 % → +0.53 / +0.46 / +0.40 R; it is driven by three
simple facts, turned into a points rule (+1 each): yesterday's RTH candle AGAINST the gap, open OUTSIDE yesterday's RTH range,
09:30–09:44 closes IN the gap direction. **Score ≥ 2:**
| version | trades/yr | win | R:R | R/trade 2010–19 / 2020–23 / 2024–26 | total | max DD | years + |
|---|---|---|---|---|---|---|---|
| C + score ≥ 2 | ~55 | 33–36 % | 1:2.9–3.4 | +0.40 / +0.41 / +0.42 | +335 R | 22.6 R | **17/17** |
| C + score ≥ 2 + add-on | ~55 | 25–29 % | 1:4.3–5.2 | +0.67 / +0.72 / +0.67 | +561 R | 38.3 R | 15/17 |
Caveat: TEST 2024–26 had already been looked at for earlier variants; the score was built from train-period features and the
logit cut chosen on train, but the family was explored with knowledge of earlier TEST results.

## Re-entry and personal-account Monte-Carlo (reentry.py, montecarlo.py)
- Re-entry after a stop-out before 12:00, on the first close back beyond the OR level: +0.05 / +0.16 / +0.33 R (weak in
  2010–19) — optional. Re-entry on the session average price: negative.
- 10,000 resampled years of 55 trades (score ≥ 2, assumes the 2010–26 edge persists):
  | version | risk per R | losing years | median year | 5th pct | 95th pct | median max DD | 95th pct DD |
  |---|---|---|---|---|---|---|---|
  | no add-on | 1 % | 10 % | +23 % | −5 % | +65 % | 9 % | 16 % |
  | no add-on | 2 % | 11 % | +46 % | −12 % | +158 % | 17 % | 30 % |
  | add-on | 1 % | 11 % | +37 % | −9 % | +126 % | 13 % | 24 % |
  | add-on | 2 % | 13 % | +77 % | −20 % | +361 % | 24 % | 43 % |

## Out-of-market check of the score (score_oom.py) — does NOT generalise
Unchanged rules on CFDs: SPX score ≥ 2 −0.16 / +0.27 / −0.18 R (vs all +0.07 / +0.26 / −0.09); gold +0.13 / +0.11 / −0.02 R
(vs +0.10 / +0.08 / −0.05). → The score is either NQ-specific or partly fitted to NQ history. Paper/sim trade before real money.

## Score on the original alert-bot versions (score_orig.py; OR-direction point from the first 5 minutes)
Alert bot 2:1: −0.04 / +0.04 / +0.05 R with score ≥ 2 (vs −0.04 / −0.04 / −0.06). No-TP 3×ATR: +0.14 / +0.21 / +0.23 R
(vs +0.14 / +0.19 / +0.08). Helps only after 2020 → weak evidence.

## Re-test of earlier edges on REAL NQ 2010–19 (retest_real.py) — the CFD verdicts were wrong
| edge | 2010–19 (real NQ) | 2020–23 | 2024–26 |
|---|---|---|---|
| Pre-Open Fade (|z|>2, TP 0.5×, SL 1.0×, exit 13:00) | 173 tr, 70.5 % win, +0.06 R | 78, 76.9 %, +0.18 R | 57, 75.4 %, +0.15 R |
| Williams VB (0.6×range, stop 0.5×range, close) | 1571, 43.7 %, +0.03 R | 647, 48.8 %, +0.08 R | 427, 45.4 %, +0.10 R |
| Open-drive follow (1:2) | 328, 39.6 %, +0.07 R | 128, 41.4 %, +0.13 R | 106, 40.6 %, +0.08 R |
All positive in all three periods on real futures (on the HistData CFD 2012–19 they were flat/negative).

## NQ multi-edge portfolio on real data 2010–26 (portfolio.py; 1 R per trade per edge)
Daily-R correlations are low (GapFB vs PF −0.04, vs WVB 0.23, vs OD 0.12). NA / NA-FVG fail on real 2010–19 (retest_na.py).
| portfolio | total | max DD | return/DD | years + | R per year 2010–19 / 2020–23 / 2024–26 |
|---|---|---|---|---|---|
| GapFB-C | +385 | 33.8 | 11.4 | 14/17 | +31 / +37 / +14 |
| GapFB-C score ≥ 2 | +335 | 22.6 | 14.8 | 17/17 | +24 / +29 / +29 |
| **GapFB score + Pre-Fade** | +368 | 20.0 | **18.4** | **17/17** | +25 / +33 / +34 |
| GapFB + PF + WVB | +555 | 40.0 | 13.9 | 14/17 | +39 / +56 / +37 |
| GapFB + PF + WVB + OD | +599 | 47.9 | 12.5 | 15/17 | +42 / +61 / +40 |
| GapFB score + PF + WVB + OD | +550 | 41.4 | 13.3 | 15/17 | +34 / +53 / +55 |

## Other CFD-era verdicts re-tested on real NQ 2010–19
- WhatsApp Monday London-sweep rule (qt_london/london_sweep_real1019.py): 2010–19 −0.06 R, 46 % win → the failure stands.
- **Opex-Friday short at 09:30** (opex_real.py), stop 0.4σ, target 0.8σ (1:2), exit 15:55, ~12 trades a year:
  2010–19 +0.39 R (49 % win) · 2020–23 +0.43 R (49 %) · 2024–26 +0.85 R (64 %); other Fridays −0.12 / −0.10 / −0.42 R.
  Positive at k 0.25 as well (+0.30 / +0.02 / +0.64). A real calendar edge on futures.

## Portfolio v2 on real data (portfolio2.py) — opex short is uncorrelated (corr 0.00 with every edge)
| portfolio | total | max DD | return/DD | years + | R per year 2010–19 / 2020–23 / 2024–26 |
|---|---|---|---|---|---|
| Opex short alone | +91 | 6.9 | 13.1 | 15/17 | +6 / +6 / +12 |
| GapFB-score + PF | +368 | 20.0 | 18.4 | 17/17 | +25 / +33 / +33 |
| **GapFB-score + PF + Opex** | **+459** | **21.2** | **21.7** | **17/17** | **+30 / +39 / +45** |
| GapFB-score + PF + Opex + WVB | +596 | 32.3 | 18.4 | 15/17 | +36 / +53 / +64 |
| GapFB + PF + Opex + WVB + OD | +690 | 46.2 | 14.9 | 16/17 | +47 / +66 / +52 |
Pine: pine/gapfb_nq.pine, pine/preopen_fade.pine, pine/opex_short.pine (run on separate charts / accounts).

## Event days (events.py) — do NOT skip them
GapFB-score: NFP (first Friday, 2010–26) +1.08 R (n 47) vs +0.37 R; CPI (2020+) +0.65 vs +0.40; FOMC days (2020+) +0.74 vs +0.40.
Pre-Fade: NFP +0.14 vs +0.10, CPI +0.18 vs +0.17 (no difference; FOMC n = 4).

## Pre-Fade refinement (pf_grid.py; train 2010–19 → validate 2020–23 → test)
Best train/validate family: 60-min window, |z| > 2.5, TP 0.5× move, SL 1.5× move: 79 % / 81 % / 81 % wins, +0.11 / +0.17 /
+0.13 R (R:R ≈ 1:0.33). TEST is not better than the base (z 2, SL 1.0×: +0.15 R, 75 %) → keep the base; the z2.5/SL1.5
version is an option for an ~80 % win rate at the same expectancy.

## Opex short refinement (opex_grid.py)
Every top train config enters at 09:30 (later entries lose the edge); k 0.4–0.8, r 1–3, exit 12:00 / 15:55 all positive in
train and validate. TEST: base (09:30, 0.4σ, 1:2, 15:55) +0.85 R beats the refined picks (+0.38…+0.43 R) → keep the base.

## Volume filters (rvol.py) — inconsistent, not adopted
RVOL of the first 15 minutes and pre-market volume quartiles: no monotone or consistent pattern across periods.

## Prior-day volume profile (vprofile.py) — inconsistent, not adopted
Open beyond yesterday's value area vs inside, and |open − POC| quartiles: no pattern that holds in all periods.
