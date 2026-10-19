# Loop state — target: OOS win ≥ 70 % AND planned R:R ≥ 1:2 (realised ratio reported), net of 2.25 pt, robust. Never relaxed.

Funnel per hypothesis: select on 2020–23 → check 2024–26 once → neighbourhood (all neighbours must stay positive) → ≤ 1 trade/day unit.
Baseline for 1:2 with no edge: 33–35 % wins.

## Best so far (all fail the 70 % bar)
| candidate | win | realised RR | exp | status |
|---|---|---|---|---|
| Pre-Open Fade 1:2 (z>2.5) | 50.6 % | 1.94 | +0.45 R | PROVISIONAL |
| Monday London sweep → Friday liquidity (1:2 variant) | 60 % | 1.65 | +0.36 R | PROVISIONAL (n = 40) |

## Done before the loop
alt charts 25,740 · ML 360 · evolutionary 380,000 · influencers 46 · DFR 3,733 · correlated FVG 11 M · QT/London 398.

## Queue (next first)
1. ~~Edge stacking~~ (done, iter 1)
2. ~~Meta-labelling~~ (done, iter 2)
3. Economic calendar — FOMC done (iter 3, fail); CPI/NFP pre-open still open
4. ~~Cross-asset SMT/PSP~~ (done, iter 4)
5. ~~Volatility-regime conditioning~~ (done, iter 5)
6. ~~Intraday volatility contraction~~ (done, iter 6) (NR-n bars inside the day) → breakout 1:2.
7. ~~Overnight inventory~~ (done, iter 7) (ON range position + gap) → first-hour continuation/reversal at 1:2.

8. (done, iter 8) CPI / NFP days — pre-open move fade/follow at 1:2 (dates: BLS schedule; NFP ≈ first Friday).
9. (done, iter 9) Leveraged-ETF rebalancing flow (Cheng & Madhavan): |day move| > k σ at 15:30 → continuation to the close, 1:2.
10. (done, iter 10) Gap fill: gap size buckets, target = prior close, stop sized for ≥ 1:2.
11. (done, iter 11) Failed opening-range breakout: first OR break that closes back inside → fade to the other side (≥ 1:2).
12. (done, iter 12) Liquidity-spike fade: 1-minute bar with range > k × average and long wick → fade, 1:2.
13. (done, iter 13) Turn-of-month / pre-holiday intraday long with 1:2 brackets.
14. (done, iter 14) Monday / weekly-open behaviour (Sunday gap, Monday range vs Friday) at 1:2.

15. (done via HistData) long-history data NSX/SPX/DXY 1-minute 2012–2025
16. (done, iter 22) Cross-asset lead-lag at 1 minute (ES/YM leading NQ) at 1:2 — needs 15.
17. (done, iter 22) SMT/PSP on long 1-minute history with structural targets — needs 15.
18. (done, iter 18 — candidates fail pre-2020) Pre-2020 out-of-sample check of the provisional candidates (Pre-Open Fade, Monday London) — needs 15.
19. (done, iter 19) VIX / 10-year yield daily regime (FRED, free) as a filter for the validated edges at 1:2.

## Iterations
### Iter 1 — edge stacking (24 configs) → FAIL
≥2 or ≥3 agreeing validated signals, 1:2–1:3 brackets. Best: k=3, stop 0.5σ: 55 % / 48 % wins (TRAIN/TEST), +0.15/+0.07 R.
Stacking adds ~5–10 pts of win rate, nowhere near 70 % at 1:2. Queue item 1 closed.
### Iter 2 — meta-labelling on validated-edge events (60 configs) → FAIL
1,223 first-of-day events (NA, WVB, PM). Best TEST win 59 % (n = 27, realised RR 0.91); at n ≥ 60 ≤ 51 %. Base 39–42 %. ML lifts ~10 pts, not 30.
### Iter 3 — FOMC days (53 days; 105 configs) → FAIL
Pre-FOMC drift, 14:00 spike follow/fade, presser reversal at 1:2–1:3. Nothing ≥ 50 % in TRAIN; TEST all negative. (CPI/NFP still open → iter 3b.)
### Iter 4 — SMT / PSP across NQ-ES-YM (Yahoo 1h 2.4 y + 5m 70 d; 48 configs) → FAIL
Every config negative in TRAIN and TEST (best −0.10 R; wins 20–36 % at 1:2–1:3). Divergence at a fresh extreme with the stop at
that extreme gets run more often than it reverses.
### Iter 5 — regime conditioning of validated edges (156 configs) → FAIL
Best TRAIN win 65.7 % (Afternoon, mid vol) → TEST 41.5 %. High-TRAIN rows are late-day time exits, not 2R hits. No row ≥ 60 % in TEST.
### Iter 6 — intraday NR-n squeeze breakout (24 configs) → FAIL. Best 42 % / 42 % at 1:2, ≈ 0 R.
### Iter 7 — overnight inventory at the open (8 configs with n ≥ 40) → FAIL. ≤ 38 % at 1:2.
### Iters 8–14 — CPI/NFP, close flow, gap fill, failed OR breakout, spike fade, turn-of-month/pre-holiday, Monday (85 configs) → all FAIL
Best TEST wins: NFP fade 53 % (TRAIN 34 %), Monday break 40 %, all others ≤ 42 %. None ≥ 50 % in both halves at 1:2.
### Iter 19 — VIX / 10-year-yield regime filters (FRED) on validated edges (270 configs) → FAIL
Best: Afternoon long after 10y −5 bp: 64 % / 62 % (n = 44), mostly time exits; nothing ≥ 70 % in both halves.
### Iter 20 — liquidity magnets / rejections at PDH, PDL, PDC, ONH, ONL, weekly open, round 100/500 (128 configs) → FAIL
Best 44 % / 46 % at 1:2 (PDL rejection), ≈ 0 R.
### Data: Dukascopy blocks this container (HTTP 429 / reset). Switched to HistData.com free 1-minute NSXUSD (Nasdaq-100 CFD),
SPXUSD, UDXUSD (dollar index) 2012–2025 → unlocks queue 16–18 with 8 extra pre-2020 years (true out-of-sample).
### Iter 18 — TRUE out-of-sample 2012–2019 (HistData NSXUSD, never used for selection; cost scaled to price) → candidates DOWNGRADED
| candidate | n | win | realised RR | exp | years + |
|---|---|---|---|---|---|
| Pre-Open Fade 76 % version | 153 | 67.3 % | 0.49 | +0.003 R | 4/8 |
| Pre-Open Fade 1:2 | 90 | 31.1 % | 1.81 | −0.131 R | 3/8 |
| Monday London sweep | 51 | 41.2 % | 0.99 | −0.133 R | 2/8 |
| Williams volatility breakout | 1,251 | 45.1 % | 1.37 | +0.054 R (t 1.56) | 5/8 |
Pre-Open Fade and Monday London did not exist before 2020 → regime-specific, not structural. (Caveat: CFD pre-market quotes.)
Lesson for the loop: every future candidate must also pass 2012–2019.
### Iter 21 — whole portfolio on TRUE out-of-sample 2012–2019 → FAIL
Noise-Area +0.004 σ (5/8 yrs), NA-FVG 92 % −0.059 σ (t −4.7, 0/8), Afternoon −0.007 σ, Rebound +0.004 σ, Rebound-95 % −0.088 σ.
All portfolio edges are 2020+ only on this data (caveat: CFD bid quotes hurt tiny-target variants most).
### Side study — fastest eval pass (fastpass/): big size ≈ coin-flip barrier odds (34–42 % per attempt, 5–16 days);
expected 13–30 days and $360–450 to the first pass.
### Iter 22 — cross-asset on 14 years (NQ−ES spread, SMT at day extremes, dollar shocks; 56 configs) → FAIL
All 28–42 % wins at 1:2 in every period; SMT strongly negative (−0.4 … −1.1 R).
### Iter 23 — evolutionary search on 14 years (63,000 rules, fitness = worse of 2012–19 / 2020–23) → FAIL
Best rule: 58 % (2012–19) / 63 % (2020–23) at 1:2 → untouched TEST 2024–25: 39 %, −0.15 R. Even with a two-period filter the
winners do not carry forward.
## Queue (new)
24. Other markets tradable at Lucid with free long 1-minute history: gold (XAUUSD ≈ GC) and crude (WTIUSD ≈ CL) from HistData —
    same funnel (three periods).
25. Session-specific structures in those markets (London fix for gold, EIA Wednesday 10:30 for crude).
### Iter 24a — gold (XAUUSD ≈ GC, 08:20–13:30, 2012–2025), evolutionary search → FAIL
Best: 50 % (2012–19) / 54 % (2020–23) → TEST 2024–25 42 %, +0.06 R. Nothing near 70 % at 1:2.
(Crude: HistData has no 2024–25 WTI files → periods 2012–17 / 2018–20 / TEST 2021–23.)
### Iter 24b — crude (WTIUSD ≈ CL, 09:00–14:30, 2012–2023; periods 2012–17 / 2018–20 / TEST 2021–23) → FAIL
Best 50 % / 54 % → TEST 39 %, −0.25 R.
### Iter 25 — EIA Wednesday 10:30 (crude) and London PM fix 10:00 NY (gold), fade/follow at 1:2–1:3 (24 configs) → FAIL
All 25–40 % wins, strongly negative after costs.

## Status after 25 iterations
Free price-only data is exhausted for this target: NQ 2012–2026 (two sources), ES, YM, DXY, gold, crude; ~650 K rule/config tests
plus 11 M correlated-FVG combinations. Best genuinely out-of-sample results never exceed ~60 % at planned 1:2.
## Queue (new — data-dependent)
26. True order-flow (Databento trades / MBP-1 for NQ) — needs the user's Databento key and budget.
27. Other index CFDs on HistData (DAX GRXEUR, Nikkei JPXJPY, FTSE UKXGBP) to look for structural effects transferable to NQ.
28. Options-derived data (GEX / 0DTE) — paid sources only.
### Iter 26 — web batch (Yu-Rentzler-Wolf overnight reversal on NQ futures; Reddit 'open model'; fade to NY open; 33 rules,
three periods 2012–19 / 2020–23 / 2024–26) → FAIL for the target
- Open model long-only (+kσ above the open → close): positive in all three periods (+0.03 … +0.12 σ, 53–61 % wins) — first rule
  that survives pre-2020, but vs a same-minute random-day long control the excess is small/inconsistent (control wins at k = 0.5
  in two periods); at 1:2 brackets it is negative. → weak drift + momentum, not a 70 %/1:2 edge.
- Overnight reversal: inconsistent sign across periods. Fade to NY open: negative everywhere.
## Queue (web sources to mine next)
29. (done, iter 27) TradingView public strategy scripts tagged NQ/ES with open source (rank by likes) — port rules, three-period test.
30. (done, iter 29) Quantpedia free strategy pages on index futures intraday.
31. (done, iter 28) Academic: Corte-Kosowski-Wang overnight reversal across futures; Lou-Polk-Skouras intraday/overnight clientele.
### Iter 27 — TradingView scripts (NY VIX Channel Trend; Opening Drive Continuation NQ; 75+48 configs, three periods) → FAIL for target
- VIX channel: ≈ 0 to +0.08 R, 40–55 % wins.
- Opening drive (1-minute candle body ≥ k × 20-bar avg range between 09:50 and 10:20, follow, bracket ≈ 1:1.5 scaled to price):
  31/75 variants positive in all three periods incl. 2012–19; most robust k 2.5, window 09:50–10:20, 30/45: +0.21/+0.22/+0.26 R,
  49–53 % wins, but only 6–12 trades a year. Weak, rare — PROVISIONAL (not 70 %/1:2).
### Iter 28 — Corte-Kosowski-Wang cross-sectional overnight reversal (NQ vs ES/gold/crude/DXY ranks) → FAIL
2012–19 −0.09 σ (45 %), 2020–23 +0.15 σ, 2024–25 +0.12 σ; 1:2 brackets 34–38 % wins.
### Iter 29 — minute-of-day seasonality (450 slot × condition tests, three periods) → FAIL
124 same-sign-in-all-periods vs ≈ 112 expected by chance; best min |t| 1.48 (15:00 continuation on down days). No tradable drift.
## Queue
32. (done, iter 30) Calendar microstructure.
33. (done, iter 31) Daily-bar exhaustion.
34. (done, iter 32) Vol-of-vol.
### Iter 30 — calendar microstructure (opex, quad witching, Monday after opex, opex week, month turn, pre-holiday; 420 configs,
three periods) → FAIL for the target, one PROVISIONAL calendar effect
- Max min-win across periods 52.8 %; nothing near 70 % at 1:2. Baseline (all days) 0/42 configs positive in all periods; 29/420 overall.
- Opex Friday SHORT at the 09:30 open, stop 0.25σ / target 0.5σ, exit close: positive in all 9 (k × period) cells.
  2012–19 +0.13 R (41 % win, placebo p 0.03) · 2020–23 +0.09 R (38 %, p 0.07) · 2024–26 +0.71 R (61 %, p 0.00); other Fridays −0.18…−0.31 R.
  12 trades a year, uneven by year (2014/15/17/18/21/23 slightly negative). Real-looking but weak → candidate filter, not a strategy.
### Iter 31 — daily-bar exhaustion (N-day extreme close, 3–5 day streaks, climax range) + intraday reversal back through the open,
1:2, 162 configs, three periods → FAIL
First version showed 64 % / +0.75 R on almost every day — a LOOK-AHEAD bug (entry before minute T while using the T-minute extreme
as the stop). Fixed (entry only from minute T, stop = extreme known at entry): max min-win 42 %, 0/162 positive in all periods.
### Iter 32 — volatility-of-volatility (day after VIX ±10/15/20 % change, VIX z ≥ 2 / ≤ −1.5, VIX top/bottom quintile; 378 configs)
→ FAIL. Baseline 0/42; 30/378 positive in all periods but best min-win ≈ 44 % at 1:2 and min R ≤ +0.09.
## Queue
35. (done, iter 35) Index CFDs on HistData (DAX GRXEUR, Nikkei JPXJPY, FTSE UKXGBP) — overseas session close → NQ open lead-lag at 1:2 (was item 27).
36. Opex-Friday short as a filter/overlay on the eval-engine ledger (does it raise pass % without lowering the win rate?).
### Iter 33 — old market-profile / pit-era ideas (Dalton overnight inventory, prior/virgin POC magnet, poor high/low repair,
Taylor 3-day cycle; TPO profiles; 24 h data NSXUSD 2012–19 + Databento 2020–26; 19 rules) → FAIL
- POC magnet (open ≥ 0.5σ from the prior / nearest virgin POC → trade toward it, stop half the distance): positive in all three
  periods but tiny: +0.04 / +0.09 / +0.09…+0.12 R, 39–45 % wins. A real but small magnet — nowhere near 70 % at 1:2.
- Overnight inventory, poor highs/lows, Taylor buy/short-day violations: negative or inconsistent.
## Queue
37. (done, iter 34) Osler (2003, FX) round-number order clustering: take-profits at round numbers → reversal on first touch; stops just beyond →
    acceleration after the cross. NQ 100/50-pt levels at 1:2.
### Iter 34 — Osler round-number order clustering (NQ 100/50/25-pt levels, fade first touch / break-out, 18 configs) → FAIL
All 18 negative in every period; win 13–36 % at 1:2 ≈ the random-entry barrier (33 %) minus costs. No round-number effect on NQ.
## Queue
38. (done, iter 36) Ehlers cycle tools (Hilbert sine-wave / MESA cycle mode) on 1–5 min bars — cycle-mode turning points at 1:2.
39. (done, iter 37) Lunar / Bradley-siderograph style calendar folklore (cheap placebo-controlled check, expected null).
### Iter 35 — overseas lead-lag into the NQ open (HistData DAX GRXEUR, Nikkei JPXJPY: residual catch-up vs NQ over the Europe /
Tokyo windows, three-market agreement follow/fade; 48 configs) → FAIL. 1/48 positive in all periods (+0.03 R), max min-win 37 %.
### Iter 36 — Ehlers Hilbert sine-wave (cycle mode) / instantaneous trendline (trend mode), 5 & 15 min, 18 configs → FAIL
All negative in 2012–19 and 2020–23; win 29–43 % at 1:2 ≈ random-entry barrier.
### Iter 37 — lunar cycle (Dichev-Janes new-moon effect), placebo by random phase shifts → FAIL (null as expected)
New-minus-full spread +0.01 / +0.03 / −0.08 σ, placebo p 0.42 / 0.32 / 0.81; 1:2 brackets 32–37 % wins.
## Queue
40. (done, iter 38) Month-end / quarter-end pension rebalancing conditioned on month-to-date equity return (and vs 10-y yield change):
    large MTD gains → sell into the last 1–3 sessions (15:00–16:00 MOC window), large MTD losses → buy. At 1:2.
41. (done, iter 39) Other HistData cross-asset leads not yet used: USDJPY (risk-on/off carry), XAGUSD, BCOUSD → NQ open.
### Iter 38 — month/quarter-end rebalancing conditioned on MTD move (126 configs) → FAIL
3/126 positive in all periods (≈ chance); quarter-end variants n = 13–42 per period; max min-win 42 %.
### Iter 39 — cross-asset overnight leads (USDJPY, silver, Brent residual vs NQ overnight; catch-up / fade; composite; 96 configs)
→ FAIL. 3/96 positive in all periods (≈ chance), max min-win 36 %.
## Queue
42. (done, iter 40) Dalton four open types (open-drive / open-test-drive / open-rejection-reverse / open-auction) classified at 10:00 from
    1-minute structure → conditional continuation/reversal at 1:2.
### Iter 40 — Dalton open types at 10:00 (OD / OTD / ORR / OA; follow & fade; inside/outside prior range; 200 configs) → FAIL for
target; OPEN-DRIVE FOLLOW is a second weak, robust survivor
- Open-drive (first-30 extreme at the open, close at 10:00 ≥ 0.2–0.5σ away) → follow at 10:00, 1:2: positive in all three periods
  across most neighbours: e.g. d0.2 k0.4 +0.14 / +0.18 / +0.11 R, 42–43 % wins, ≈ 40 trades a year. Consistent with iter 27b.
- OTD / ORR / OA and all fade variants: ≈ zero or negative. Max min-win 42 %.
## Queue
43. (done, iter 41) Confluence of the weak survivors (open-drive follow, POC magnet direction, opex-Friday short, Reddit open-model long):
    does agreement raise the win rate toward 70 % at 1:2? (expected: only marginally — check with the honest funnel).
### Iter 41 — confluence of the weak survivors (OD, POC magnet, open-model, opex) at 10:00 → FAIL
Agreement does NOT raise the win rate: OD alone (k0.4: 42–43 %, +0.11…+0.18 R) is the best robust row; 'OD & POC agree' flips
negative in 2024–26; score ≥ 3 has n = 10–27 per period. Opex works only at the 09:30 entry, not at 10:00.
## Queue (new free data families)
44. (done, iter 42) VIX term structure (CBOE VIX9D / VIX / VIX3M daily CSVs, free): contango/backwardation & 9-day/30-day ratio → next-day
    intraday direction / range at 1:2.
45. CBOE daily put/call ratios (equity / index / total, free archive) — sentiment extremes → next-day NQ at 1:2.
### Iter 42 — VIX term structure (CBOE VIX9D/VIX, VIX/VIX3M: deciles, jumps, backwardation, deep contango; 294 configs) → FAIL
8/294 positive in all periods (baseline 0/42), max min-win 47 %, no row near 70 % at 1:2.
45. (skipped) CBOE free put/call archive ends 2019-10 → no 2020+ out-of-sample possible; not testable under the funnel.
46. (done, iter 3) Lucca-Moench pre-FOMC drift (equities rise into the 14:00 announcement): FOMC-day 09:30→13:59 long and day-before variants at
    1:2; dates from federalreserve.gov calendars (fetched, not typed from memory).
47. (done, iter 43) Turnaround Tuesday' / Monday-range weekly structure at 1:2.
### Iter 43 — weekly-structure folklore (Turnaround Tuesday, Monday after down Friday, etc.; 336 configs) → FAIL
6/336 positive in all periods (≈ chance), max min-win 47 %. (Queue 46 pre-FOMC drift was already tested in iter 3 → fail.)
## Status after 43 iterations
Free data is exhausted for the 70 % / 1:2 target. Robust (all-period) survivors are all weak, 40–60 % wins at ~1:2:
open-drive follow (+0.1–0.2 R), opex-Friday short at 09:30 (+0.1–0.7 R, 12/yr), POC magnet (+0.04–0.12 R), Reddit open model.
Remaining untested families need paid / user-supplied data: 26 order flow (Databento MBP-1/trades), 28 options GEX / 0DTE.
### Iter 44 — GapFB (author 'Ace Trades') reconstructed from alerts; no-TP time-exit variant → BEST ROBUST EDGE SO FAR (not 70 %)
Real NQ 2010–26 (user's Databento file). Gap ≥ 0.3 % + 5-min OR stop entry, stop 3×ATR(1m), no target, exit 15:55:
24–27 % wins, R:R 1:3.0–3.7, +0.14 / +0.19 / +0.08 R, 15/17 years positive; placebo (non-gap days) negative. Max DD 51 R.
The posted 2:1-target version loses (34 % ≈ random barrier). See research/gapfb/README.md.
### Iter 45 — GapFB improvement funnel (7,776 configs train → validate → test) + pre-entry filters
Best family: 15-min OR, gap direction only, 2×ATR stop (+5×ATR trail), entry ≤10:30, exit 15:55: +0.32/+0.32/+0.13 R
(train/val/TEST), ~33 % win at 1:3. Filters: 'yesterday against gap' strong in train+val, fails TEST. TEST edge weak (t ≈ 1).
## Queue
48. GapFB-C as a multi-market portfolio (ES via SPXUSD CFD 2012–25, gold XAUUSD; ES/YM futures if the user uploads them).
49. Eval sizing for GapFB-C (Lucid 50K: $2K EOD trailing, 50 % consistency) — pass %, days, with 1–3 MNQ and daily caps.
### Iter 46–47 — GapFB-C multi-market (NQ-specific; SPX/gold add drawdown) and Lucid eval sizing ($200 risk → 54 % pass, ~95 days)
## Queue
50. (done, iter 48) GapFB-C execution sensitivity: entry 1–2 minutes late / extra slippage (the author says late entry kills it).
51. GapFB-C + eval-engine edges (WVB, Noise-Area, Pre-Fade) as one eval policy (research/evalbot/sim.py).
### Iter 48 — GapFB-C latency: 1 min late kills 2024–26 (+0.13 → −0.01 R) → resting stop order at 09:45 required
### Iter 49 — 24 h session anchors (gap/pre-move + OR breakout at 18:00…15:00; 2,184 configs, train 2010-19) → only the NY open works
Best t per anchor (train): 09:30 4.1, 10:00 2.4, 15:00 2.0, 11:30 1.5, London 03:00 0.7, Asia/Tokyo/Frankfurt/08:30/13:00/14:00 ≤ 0.1.
Validate 2020-23: only 10:00 'with' 5-min OR survived (+0.25 R, t 2.0) → TEST 2024-26 +0.02 R → FAIL.
## Queue
52. (done, iter 50) Personal account: hold GapFB-C winners overnight (exit next 09:29 / next 15:55, trail continues) — swing extension.
53. (done, iter 51) Failed-breakout reversal: GapFB OR break that closes back inside the OR within N minutes → reverse.
### Iter 50 — GapFB-C held overnight (next open / next close / multi-session trail) → no gain (2024-26 +0.04…+0.07 vs +0.11 R same day)
### Iter 51 — failed-breakout reversal (OR break closes back inside within 5/15/30 min → reverse; 1:2, 1:3, trail) → FAIL (negative almost everywhere)
## Queue
54. (done, iter 52) Zone breakouts at the open: overnight high/low and prior-day high/low as the trigger (instead of the 15-min OR), gap direction.
55. (done, iter 54) Day-2 continuation: the session after a qualifying GapFB-C winner — same direction OR break.
56. (done, iter 55) Intraday second leg: after GapFB-C entry reaches +1R, add a second unit on the first 1-min pullback to the 20-EMA.
### Iter 52–55 — zones (ON/PD high-low breakouts and fades: negative), day-2 continuation (fail), ADD-ON to GapFB-C winners
(+0.49/+0.21/+0.34 R per add-on unit, robust to arm level and EMA length) → adopted: GapFB-C + add-on = best so far.
## Queue
57. (done, iter 56) GapFB-C exit refinements: trail tightening after 14:00 / at +3 R, and partial (½ at +2 R).
58. (done, iter 57) GapFB-C entry refinements: stop-limit vs stop, 1-tick buffer above the OR, skip if OR width > k×ATR.
### Iter 56–57 — GapFB-C exits (none beat the 5×ATR trail) and entries: OR-width ≥ 3.5–4×ATR filter improves every period
(w4: +0.35/+0.49/+0.37 R, ~37 trades/yr). Current best = GapFB-C + OR-width ≥ 3.5–4 ATR + add-on.
## Queue
59. (done: stats iter 58, Pine pine/gapfb_nq.pine — needs a TradingView compile check) Combine OR-width filter + add-on; full stats and Pine port of the final rules.
### Iter 58 — final GapFB-NQ table (final.py): C + OR≥3.5–4 ATR (+ add-on) best; see gapfb/README.md
## Queue
60. (done, iter 61) GapFB-NQ on MNQ vs NQ costs / 1-contract granularity; Monte-Carlo of yearly outcomes for a personal account (risk 1 % per R).
61. (done, iters 59–60) New families for the NY open: first-hour VWAP reclaim after GapFB stop-out; gap-fill vs gap-and-go classifier (pre-entry features → logistic, train 2010-19).
### Iter 59 — quality score for GapFB-C (yday against + outside range + first-15 with gap ≥ 2) → BEST: +0.40/+0.41/+0.42 R,
17/17 years positive, DD 22.6 R; with add-on +0.67/+0.72/+0.67 R. Pine updated (minScore input, add-on optional).
### Iter 60–61 — re-entry at the OR after stop-out (weak +0.05/+0.16/+0.33, optional); Monte-Carlo personal account
(score ≥ 2, 1 % per R: median year +23 %, 10 % losing years, 95th pct DD 16 %).
## Queue
62. (done, iter 62) Out-of-market check of the score rule: GapFB-C + score ≥ 2 on SPX and gold CFDs (no re-fitting) — does the score generalise?
63. (done, iter 63) Score rule on the original 5-min OR GapFB (the alert bot) and on the 1:2 target version.
### Iter 62 — score rule out-of-market (SPX, gold CFD): does not generalise (SPX worse in 2 of 3 periods) → treat the score as
NQ-specific / possibly partly fitted; base GapFB-C remains the robust core.
### Iter 63 — score on the alert-bot GapFB versions: no effect 2010-19, helps 2020+ → weak.
## Queue
64. (done, iter 64) Low-score gap days (score 0–1): trade the OPPOSITE OR break (gap-fill side) at 1:2 / trail.
65. (done, iter 65) Afternoon continuation on GapFB-C winner days: 13:30–14:00 range break in the morning direction.
### Iter 64 — low-score gap days, trade against the gap: noisy (score 0: n 11–49), score ≤1 inconsistent → FAIL
### Iter 65 — afternoon (13:30–13:44) range-break continuation on gap days: −0.31/−0.03/−0.30 R → FAIL (afternoon breaks churn)
## Queue
66. (done, iter 66) Overnight-path shape on gap days: does a gap built late (08:00–09:29) vs early (18:00–02:00) change GapFB-C? (pre-entry feature)
67. GapFB-C on real ES / YM futures once the user uploads them (out-of-market check with futures, not CFDs).
### Iter 66 — overnight path shape (share of gap built late / early) on GapFB-C days → no monotone or consistent effect → FAIL
## Queue
68. (done, iter 67) Re-test the earlier 2020+ edges (Pre-Open Fade, Noise-Area, Williams VB, NA-FVG, opex short, open-drive) on REAL NQ futures
    2010–19 (user's Databento file) — they failed on the CFD, which may have distorted pre-market/overnight prices.
### Iter 67 — earlier edges on REAL NQ 2010–19: Pre-Fade +0.06/+0.18/+0.15 R (70–77 % win), WVB +0.03/+0.08/+0.10, open-drive
+0.07/+0.13/+0.08 → all positive in all periods; the CFD 2012–19 'fails' were data artefacts for these rules.
## Queue
69. (done, iter 69) Multi-edge NQ portfolio on real data 2010–26: GapFB-C (+score) + Pre-Fade + WVB + open-drive; daily R, DD, correlation.
70. (done, iter 68) Re-test Noise-Area and NA-FVG (92 % win scalp) on real NQ 2010–19.
### Iter 68 — NA / NA-FVG on real NQ 2010–19: fail (≈0 / negative) — CFD verdict confirmed for those.
### Iter 69 — real-data NQ portfolio: best risk-adjusted = GapFB score≥2 + Pre-Fade (+368 R, DD 20 R, 17/17 years);
most profit = GapFB + PF + WVB + OD (+599 R, DD 48 R).
## Queue
71. (done, iter 70: run pine/preopen_fade.pine alongside) Pine: add Pre-Fade to the GapFB script (or run pine/preopen_fade.pine alongside) — check order overlap 09:00–13:00.
### Iter 70 — PF vs GapFB overlap: 73 of 309 PF days are GapFB-score days (PF −0.31 R there, +0.23 R elsewhere) but the
gap is only known at 09:30; filtering PF by the 08:59 overnight move is inconsistent (n tiny) → run both independently (~4–5
overlap days a year; use separate accounts or accept netting).
## Queue
72. (done, iter 71) Real-data re-test of other rules that failed only on the CFD: Monday London-sweep rule (qt_london),
    overnight reversal (Yu-Rentzler-Wolf), opex-Friday short, Reddit open model.
### Iter 71 — real-data re-tests: London Monday rule fails (−0.06 R); OPEX-Friday short at 09:30 (0.4σ stop, 1:2):
+0.39 / +0.43 / +0.85 R, 49–64 % win, other Fridays negative → adopted as a portfolio edge (~12 trades/yr).
## Queue
73. (done, iter 72) Portfolio v2 on real data: GapFB-score + Pre-Fade + opex short (+ WVB/OD optional); Pine for the opex short.
### Iter 72 — portfolio v2: GapFB-score + Pre-Fade + Opex short = +459 R, DD 21 R, return/DD 21.7, 17/17 years → BEST PORTFOLIO.
Pine for the opex short: pine/opex_short.pine.
### Iter 73 — real-data re-runs of the calendar grid (iter30_calendar_real.py: 26/420 positive in all periods ≈ CFD's 29;
nothing beyond the opex short) and the web batch (iter26_web_real.py: same picture as CFD — open-model long weak +0.05 σ).
## Queue
74. (done, iter 74) Event days and GapFB-score / Pre-Fade: CPI, NFP, FOMC days (dates from official calendars) — include or skip?
### Iter 74 — event days: GapFB-score better on NFP/CPI/FOMC days (small n) → keep trading them; Pre-Fade unaffected.
## Queue
76. (done, iter 75) Real-data re-runs of iter32 (vol-of-vol) and iter42 (VIX term structure) — cheap, expected same as CFD.
### Iter 75 — real-data re-runs of vol-of-vol (32/378) and VIX term structure (8/294): same as CFD → no edge.
## Queue
77. (done, iter 76) Pre-Fade refinement with the funnel on real data: window (60/90/120 min), z (1.5–3), TP/SL multiples, exit time — train 2010–19, validate 2020–23, test once.
78. (done, iter 77) Opex short refinement: entry 09:30 vs 09:35/10:00, stop k grid, exit time — same funnel.
### Iter 76 — Pre-Fade grid (real data, funnel): z2.5 / SL 1.5× gives ~80 % wins in all periods but same R as base → keep base.
### Iter 77 — opex short grid: edge lives at the 09:30 entry; whole neighbourhood positive; base kept.
## Queue
79. Volume (real NQ has volume): relative volume of the first 15 minutes (vs the same window over 20 days) and pre-market
    volume as GapFB-C filters — train 2010–19 / validate 2020–23 / test.
