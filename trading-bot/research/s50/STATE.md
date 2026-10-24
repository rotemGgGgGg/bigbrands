# s50 research loop — state

## Plan (fixed before results)
- **Data:** NQ 1-minute (Databento, front month by volume) 2010-06 → 2026-07, bars 5/15/60 m, 24 h, roll-aware.
- **Periods:** train 2010–19 (selection), validate 2020–23 (confirmation), test 2024–26 (looked at once per finalist).
- **Costs:** 2.25 pt × price/17000 per round trip (≈ $6.6/MNQ at 25k, above real ≈ $2.5); stress = ×2.
- **Phase 1:** 194,400 single-strategy variants (`phase1.py`).
  - Selection: train n ≥ 300, train t ≥ 3 and R > 0 → validate R > 0 → test.
  - Multiple-testing bar: expected max |t| under null for 194k trials ≈ 4.9.
- **Phase 2:**
  - Confirmation combos: entry A filtered by state of B, for the Phase-1 survivors + their families.
  - Portfolio combos of daily R, using the existing God components (No-Wick, GapFB, Pre-Fade, Opex) as candidates too. Search: greedy/beam on train Sharpe.
- **Phase 3:** refine finalists (entry/exit variants, sessions, long/short, risk caps).
- **Phase 4:**
  - Walk-forward: 3y train → 1y test, rolling.
  - Stress costs, strict fills, 1-minute replay of finalists, random-entry placebo.
  - Deflated Sharpe, bootstrap drawdown.
- **Phase 5:** final rules + code + prop plan (Lucid Flex: fees, data, VPS, pass time, payout timeline).

## Log
- iter 1:
  - Built `bars.py`, `ind.py`, `signals.py` (all 50 templates), `engine.py`, `smoke.py`.
  - Smoke test at template defaults (15 m): **every template negative on train, in 24 h and RTH**.
  - Launched `phase1.py`.
- iter 2:
  - Phase 1 done: 0 variants above the 4.9 multiple-testing bar with a real sample.
  - Phase 2: confirmation filters (1,764) and portfolio beam (11,436) add nothing out of sample.
  - Walk-forward: best template is +0.12R OOS.
  - Payout simulation for LucidFlex 50K done.
  - **Final:** keep the God portfolio + $150 risk cap; request payouts at $3k profit. Loop complete (`RESEARCH.md`).
