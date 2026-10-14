# Research state (resume from here)

**Target:** OOS win ≥ 70 % AND planned R:R ≥ 1:2, positive net expectancy, robust. Not met. Best = PROVISIONAL Pre-Open Fade 1:2.

**Data:** MNQ 1-minute OHLCV Databento 2020-01 → 2026-10-06 (scratchpad full1m.pkl, D.pkl, instr.pkl; hunt_feat.pkl cache).
No tick/book/delta/options. numba/lightgbm not installed (declined) → numpy/sklearn.

**Splits:** TRAIN < 2024-01 · VAL 2024-01 → 2025-06 · TEST ≥ 2025-07 (unopened for stages 1–3).

## Completed (≈ 406K configs, all logged)
1. stage1_charts.py — 9 alternative chart families, 25,740 configs. 0 pass.
2. stage2_ml.py / inspect_ml.py / stage2b_ml_daily.py — HGB on 206K entry rows, 39 features. Clustering artefact found & invalidated. 0 pass.
3. stage3_evo.py — 380,000 evolutionary rules. Overfit (train 70 % → val 45 %). 0 pass.
4. theory_and_prefade.py — drift bound; best_strategy/ — provisional candidate with walk-forward/bootstrap/stress.

## Exact next steps (if the loop continues)
1. Data that could change the answer (must be acquired by the user — costs money, not done): tick/order-book or true delta (e.g. Databento MBP/trades), options/GEX, ES & other futures with long 1-minute history.
2. Cross-asset lead-lag (NQ vs ES/ZN/DX) once the data exists.
3. Pre-open fade: add the 08:30 economic calendar (CPI/NFP flag) as a filter — hypothesis: win rate concentrates on scheduled-release days.
4. Re-run stage 3 with a stricter fitness (VAL-penalised nested CV) only if a new data source adds features.
