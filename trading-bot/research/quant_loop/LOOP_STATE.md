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
40. Month-end / quarter-end pension rebalancing conditioned on month-to-date equity return (and vs 10-y yield change):
    large MTD gains → sell into the last 1–3 sessions (15:00–16:00 MOC window), large MTD losses → buy. At 1:2.
41. Other HistData cross-asset leads not yet used: USDJPY (risk-on/off carry), XAGUSD, BCOUSD → NQ open.
