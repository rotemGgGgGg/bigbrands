# NQ/MNQ creator & ICT strategy research — validation report (2026-10-24)

## Verdict
**No independently validated candidate.** Of 1,020,000 tested configurations and 12 replicated creator strategies, none
passed the pre-registered train → validation funnel. The 2024–2026 holdout was **not used**, because nothing reached it.
It remains untouched for future work.

## What was done
| Step | Result |
|---|---|
| Read both spreadsheets | 17 leads + 8 rejected controls; 75 research leads (all rows, all URLs) |
| Sources inspected | 25 public GitHub repos cloned; READMEs, rule files and published results read; TradingView pages fetched where needed |
| Data | NQ 1-minute 2010-06 → 2019 (Databento NQ, front month by volume) + MNQ 1-minute 2020 → 2026-10 (Databento) |
| Engine | `ict_engine.py`: one causal minute-by-minute state machine (see below) |
| Look-ahead audit | `audit.py`: scrambles every bar after a random cut, rebuilds the levels from the scrambled data, and requires identical decisions up to the cut. **957 checks, 0 violations.** |
| Costs | MNQ $1.50 round trip (0.75 NQ pt) + 1 tick on every market-type fill; limits fill only when price trades 1 tick through |
| Periods | train 2010–2017 · validation 2018–2020 · test 2021–2023 · **holdout 2024-01 → 2026-10 (untouched)** |
| Search | 1,000,000 random configurations + 20,000 evolutionary refinements (selection on train only), each with full metrics, logged to sqlite (`ict_configs.sqlite`, 1.02 M rows) |

The engine's model:
- **Sweep:** a liquidity level is swept inside the window. Levels: prior-day RTH H/L, Asia, London, overnight, 09:00 hour, opening ranges, rolling N-bar.
- **Confirmation:** none, MSS, CISD, or a displacement candle, optionally with a body filter.
- **Entry:** market at the next open, limit at the FVG (proximal / mid / distal), or IFVG close.
- **Exits:** stop at the sweep extreme, FVG distal edge, or ATR; target fixed R or opposite liquidity; break-even; time exit.
- **Filters:** bias filters, side, trades per day, stop-size band, stop for the day after a loss.

## Creator replications (2010–2023, same costs)
| Strategy (source) | Trades/yr | Win % | R / trade | Profitable years |
|---|---|---|---|---|
| Isogeny ORB pullback, **as published** (Justme-Cliff) | 206 | 51.7 | +0.135 | 12/14 |
| Isogeny ORB pullback, **causal fix** | 205 | 38.0 | **−0.262** | **0/14** |
| Isogeny Gap fill (tiny gaps) | 15 | 47.8 | −0.046 | 7/14 |
| Isogeny IB breakout | 77 | 44.1 | +0.002 | 5/14 |
| 15-Min ORB "Real Version" MNQ (TradingView) | 138 | 69.1 | −0.051 | 1/14 |
| Wieland 15-min ORB A / B / C | 243 | 50 / 35 / 50 | −0.13 / −0.12 / −0.13 | 1–3/14 |
| Silver Bullet AM (hindsight-finance) | 23 | 33.8 | −0.187 | 3/14 |
| Silver Bullet PM | 43 | 35.0 | −0.271 | 2/14 |
| ICT-bot V106 approximation (sweep → displacement → FVG, 1.1 RR) | 483 | 46.1 | −0.187 | 2/14 |
| Macro window A (08:30–09:10) sweep → MSS → FVG | 41 | 46.6 | −0.154 | 0/14 |
| PineGen daily liquidity sweep | 36 | 31.4 | −0.221 | 3/14 |

**Look-ahead found in a published repo.** Isogeny's ORB "direct" fallback enters at the open of the bar right after the
breakout, but the decision to enter is only made 4 bars later. That one line produces the whole published edge.

## Search funnel (rules fixed before looking)
| Stage | Configurations |
|---|---|
| Tested | 1,020,000 |
| F1 train: ≥ 200 trades, R > 0, t ≥ 3 | 1,839 (random search alone: 0; best random train t = 1.74; the 1,839 come from evolution optimizing train) |
| F2 validation: ≥ 60 trades, R > 0, t ≥ 2 | **0** |
| F3 test > 0 | 0 |

Of the 1,839 train-optimized configurations, only 1.3% are even positive in validation; their median validation R is
−0.07. This is the signature of overfitting.

## Statistical checks
- **Multiple testing:** the expected maximum |t| from luck alone over 1.02 M trials is ≈ 5.3. The best configuration found reaches 3.6.
- **PBO:** CSCV with 16 blocks on the 100 best train configurations gives **PBO = 0.77**. The in-sample winner usually lands in the bottom half out of sample.
- **Walk-forward:** each year, the best config from a pool of the 200 best train configs, chosen on the trailing 4 years, is traded the next year.
  - The 2018–2023 years are clean, because they are outside the data used to build the pool.
  - Result: **−15.6R over 401 trades (−0.039R/trade)**, 2 of 6 years positive.
  - The 2014–2017 years look positive, but they are inside the pool-selection data and are not evidence.
- **Earlier bug, found and fixed:** a premium/discount bias filter read the full overnight range during the London session. That produced a convincing London cluster (train t ≈ 10, 14/14 years). After the fix the cluster disappeared, and the audit was extended so this class of bug is now caught.

## Evidence quality
- **Strongest negative evidence:**
  - 1.02 M causal configurations with zero validation survivors.
  - PBO 0.77.
  - Negative clean walk-forward.
  - Independent studies in the lead list agree: LucasXCoder (25k-config Silver Bullet grid, DSR ≈ 0), Nijatzz ICT edge study, aleks-drozy follow-up, hindsight Cameron model.
- **Not tested:** discretionary judgment; tick-level sequencing; order flow; protected / closed-source scripts. These are listed in the workbook as untested.

## Files
| File | Contents |
|---|---|
| `results/ICT_NQ_research_master.xlsx` | Leads (both spreadsheets), creator replications, funnel, top 3,000 configurations, walk-forward |
| Scratchpad `ict_configs.sqlite` | All 1,020,000 configurations with metrics (440 MB, not committed) |
| `ict_creators.py` | Every replication with source references |
| `creators_summary.csv` | Replication results |

**How to run:**
`python3 ict_data.py` → `python3 audit.py` → `python3 ict_search.py 0 1000` → `python3 ict_evo.py 20 1000` → `python3 finalize.py`
