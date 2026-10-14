# Strategy hunt (Oct 2026): what survives, what doesn't

Data: Databento MNQ 1-minute 2020-01 → 2026-10. Costs 1.25 pt per round trip (+1 pt stress where noted).
Selection on 2020–23 only, 2024–26 reported. Side-sign bug in the first events run was found and fixed before any conclusion.

| Stage | Script | Tests | Result |
|---|---|---|---|
| 1. Factor conditions (pre-open + intraday state, 1–2 features, 11 times × 4 exits) | discover.py | 13,148 | IS significance does not predict OOS (47 % vs 45 % base). Noise. |
| 2. Level events (PDH/PDL/ONH/ONL/OR/open±σ, continue vs fade, TP/SL grid) | events.py | 1,760 | Only open+1σ breakout 10:00–11:00 continuation survives = intraday momentum (known). |
| 3. Entries/exits on Noise-Area momentum days (FVG, VWAP, EMA, retrace, band; K trades/day) | momo.py | 502 | Ceiling ≈ $5–10 / trade at 80–90 % wins, PF 1.1–1.4. Thin, implementation-sensitive. |
| 3b. NA-FVG with 5-minute gaps | ../winrate/fvg5m.py | 3 | Fails OOS (−$4.4 / trade). Keep the 1-minute version. |
| 4. 24h clock × past move × hold (Globex hours included) | night.py | 2,999 | 09:00 pre-open reversal stands out. |
| 5. **Pre-open fade** shaping + robustness | prefade*.py | — | **Real edge** (below). |
| 5b. Same fade rule at the 27 other clock times | fade_any.py | 168 | Does not work anywhere else (10:00–10:30 is the opposite = momentum). |

## Pre-Open Fade (pine/preopen_fade.pine)
08:00→08:59 move with |z| > 2 vs the same hour over the previous 20 days → at 09:00 trade against it.
Target 50 % retrace, stop 100 % of the move, time exit 13:00.

- 143 trades (≈ 21 / year), **76 % wins, +0.18 R / trade** (+1 pt extra slippage), IS +0.18 R, OOS +0.17 R.
- Per 1 MNQ: +$61 / trade, PF 2.57, max DD −$593, 7/7 years positive, max 2 losses in a row, 16-win streak.
- t = 3.79 (IS 2.94, OOS 2.39). Same days traded the other way: −0.17 R. Side-randomisation p < 0.0002 (still < 0.006 after ×28 clock times).
- 90/90 neighbouring parameter sets (window 45/60/90, z 1.5–2.5, target 0.75–1.25, stop 1.0–1.5) positive in both periods.
- Not driven by a few days: median trade +$121 (1 MNQ, 1.0/1.0 version); total without the best 5 days still +$8.4K.

LucidFlex 50K (prop_combo.py, $500–700 risk per trade): eval passed in 100 % of historical start dates,
but slowly — median 16–22 months (only ~20 trading days a year). EV ≈ +$1.4–1.6K per account after the fee.
Adding NA-FVG (2 MNQ) is faster but drops the pass rate to 74 %.
