# Research log — quant loop (Oct 14 2026)

## Sources consulted (with what they actually say)
- Robot Wealth / Kris Longmore — edges come from "who pays you and why"; running several small edges is the main advantage. Practitioner opinion, not statistical evidence.
- Andrea Unger (Ungeracademy) — his edge was an inefficiency (option-maker software lag), found by checking arbitrage maths. Anecdote.
- Toby Crabel / Linda Raschke / Larry Williams — searched; only book listings found, no documented origin of their patterns. Not usable as evidence.
- Princeton thesis on dealer-gamma hedging — the hedging feedback channel adds little predictive power for intraday variance. Academic; supports NOT building on GEX without options data (which we do not have anyway).
- Zarattini, Aziz & Barbon 2024 (noise-area intraday momentum) and Gao et al. (intraday momentum) — tested earlier in this repo; momentum is real on NQ; last-30-minute variant failed here.
- Dalton "80 % rule" (market profile) — tested (stage 1, profile family): does not reach 70 % at 1:2.

## Hypotheses → result
| # | Hypothesis | Where | Result |
|---|---|---|---|
| H1 | Alternative chart constructions (Renko, Heikin-Ashi, range bars, volume bars, market profile, P&F, 3-line break, approx-delta divergence, permutation entropy) reveal 1:2 setups with ≥70 % wins | stage1_charts.py | **Rejected.** 25,740 configs. Best TRAIN win (n≥100) 52.6 %; best VAL 53 % (n=15). |
| H2 | A non-linear model over ~39 cross-chart features predicts 2R-before-1R | stage2_ml.py | First pass showed 73–100 % — **artefact**: all trades on 2–3 days (Apr 24–25 2025). Invalidated. |
| H2b | Same, one trade per day | stage2b_ml_daily.py | **Rejected.** Best VAL with n≥30: 45 % (base 34–37 %). ML adds 5–8 pts. |
| H3 | Evolutionary search of 2–4-condition rules finds a hidden 70 % pocket | stage3_evo.py | **Rejected.** 380,000 rules. Elite TRAIN win 70 % → VAL 45 %; corr(train, val) = 0.038 (pure selection noise). |
| H4 | The validated pre-open fade can be reshaped to 1:2 | theory_and_prefade.py, best_strategy/ | **Provisional.** 1:2 realised 1.94, +0.45 R, positive in all three periods — but 50.6 % wins, not 70 %. |
| H5 | 70 % at 1:2 is reachable with the drifts we observe | theory_and_prefade.py | Brownian bound: needs 2μd/σ² = 1.13; our best edges ≈ 0.1–0.3 (→ 37–44 %). Explains every result above. |

## Rejected ideas (with reason) — also in experiment_results.csv `reason`
Renko reversal/pullback, HA flips/continuation, range-bar exhaustion & three-push, volume-bar absorption & ignition, profile 80 % rule & VA rejection,
P&F double/triple breaks, 3LB reversals, approx-delta divergence, entropy follow/fade: all < 55 % at 1:2 out of sample.
Earlier repo work (research/hunt, research/winrate) rejected 13 news/flow ideas, 13,148 factor tests and 1,760 level tests.

## Data limitations (not pretended away)
1-minute OHLCV only. No ticks, order book, true delta/footprint, options/GEX, or a second long-history instrument. Anything named "delta" is an OHLCV approximation.
