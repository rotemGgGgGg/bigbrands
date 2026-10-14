# Validation report

## Protocol
Chronological splits: TRAIN < 2024-01 (984 days), VAL 2024-01 → 2025-06 (365), TEST ≥ 2025-07 (311).
Stages 1–3 selected on TRAIN only and checked on VAL. **No stage-1/2/3 candidate passed VAL, so TEST was never opened for them** (correct protocol — nothing to test).
The provisional candidate (#1) comes from earlier research that had already seen 2024–2026, so its TEST figures are not a virgin hold-out. Stated, not hidden.
Costs: 1.25 pt per round trip + 1 pt stress (≈ $4.50 per MNQ). Stop wins same-minute ties. Market entries at the next minute's open; limit fills only when traded through.

## Counts (from logs, not estimated)
- Stage 1 alternative charts: 25,740 TRAIN configs (+80 VAL checks) — logs/stage1_*.csv
- Stage 2 ML: 60 VAL rows (invalidated: day clustering) + 150 TRAIN/150 VAL daily-unit rows — logs/stage2_ml.csv, logs/stage2b.csv
- Stage 3 evolutionary rules: 380,000 — logs/stage3_*.csv.gz; elite VAL checks 1,200 — logs/stage3_val_*.csv
- **Total ≈ 406,000 configurations.** Acceptance passes: **0.**

## Multiple testing
Stage 3: elite TRAIN win 70.0 % vs VAL 45.1 %, correlation 0.038 → the TRAIN winners are selection noise (≈ 100 % probability of backtest overfitting for that family).
Stage 2: an apparent 73.5 % (49 trades) was 2 days. Unit of independence = the day; all later stats use ≤ 1 trade/day.

## Candidate #1 — Pre-Open Fade 1:2 (best_strategy/run_output.txt)
| period | n | win % (95 % CI) | realised RR | expectancy R (95 % CI) |
|---|---|---|---|---|
| TRAIN 2020–23 | 49 | 46.9 (32.7–61.2) | 1.96 | +0.361 (−0.04 … +0.77) |
| VAL 2024–25H1 | 20 | 55.0 (35–75) | 1.88 | +0.517 (−0.08 … +1.10) |
| TEST 2025H2–26 | 16 | 56.2 (31–81) | 1.98 | +0.630 (−0.08 … +1.31) |
| ALL | 85 | 50.6 (40.0–61.2) | 1.94 | +0.449 (+0.15 … +0.75) |
Years: 2020 −0.39 R, 2021 +0.33, 2022 +0.71, 2023 +0.54, 2024 +0.79, 2025 −0.16, 2026 +1.03 (5/7 positive).
Long +0.47 R / short +0.43 R. Extra cost 0/2/4 pt: +0.47 / +0.43 / +0.40 R. Max DD −6.4 R, max 6 losses in a row.
Neighbourhood (z 2.0–3.0 × target 0.75–1.25): all 15 positive (+0.16 … +0.66 R); win rises with z (40 % → 60 %) as n falls (143 → 50).

## Acceptance criteria — candidate #1
| criterion | met? |
|---|---|
| OOS win ≥ 70 % | **NO** (55–56 %, CI upper ≈ 75–81 %) |
| planned R:R ≥ 1:2 | yes |
| realised win/loss ratio reported & credible | yes (1.94) |
| positive net expectancy after costs | yes (+0.45 R; CI excludes 0 on all data, not per split) |
| sufficient sample / uncertainty | weak (85 trades in 6.75 years) |
| walk-forward / robustness | fixed rule, 5/7 years positive, neighbourhood all positive |
| no look-ahead / unrealistic fills | yes (decision at 08:59 close, fill 09:00 open) |
| account risk (LucidFlex $2K EOD) | with $300 risk/trade: max DD −6.4 R = −$1,920 — at the limit |
**Verdict: PROVISIONAL, not validated.**

## Why 70 % at 1:2 was not found
For Brownian motion with drift, P(+2d before −d) = 70 % needs 2μd/σ² ≈ 1.13. A random entry gives 33.3 % (measured 35.3 %).
The strongest real NQ intraday drifts we measured correspond to ≈ 0.1–0.3 (37–44 %). Reaching 70 % would need an edge ~4–10× stronger than anything that survived out-of-sample in ~424K tests across this repo.
