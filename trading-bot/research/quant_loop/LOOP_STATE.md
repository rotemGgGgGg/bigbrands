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

15. Free long-history data: Dukascopy USATECH/USA500/USA30 1-minute (CFD proxies of NQ/ES/YM) 2015–2026 — background download.
16. Cross-asset lead-lag at 1 minute (ES/YM leading NQ) at 1:2 — needs 15.
17. SMT/PSP on long 1-minute history with structural targets — needs 15.
18. Pre-2020 out-of-sample check of the provisional candidates (Pre-Open Fade, Monday London) — needs 15.
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
