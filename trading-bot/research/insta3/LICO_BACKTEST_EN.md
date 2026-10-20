# LICO Model — 16-Year Backtest on Nasdaq Futures (NQ / MNQ)

**Result: no edge.** All 32 mechanical versions of the model lose money over 2010–2026.
Even with **zero commissions and zero slippage**, the best version earns about **+0.01R to +0.03R per trade**, which is coin-flip territory.

---

## 1. The model as presented in the video
Source: Instagram reel by @ksbtrades, *"How I was able to drop out at 21 through this strategy"*.

- **Before 9:30 ET:** mark draws on liquidity. These are session highs and lows, plus swing highs and lows on the 15-minute chart.
- **9:30–10:30 ET:** wait for a liquidity sweep of one of those levels. This is the **L** (Liquidity sweep).
- **Confirmation on the 1-minute chart:** look for an **IFVG** (I) and a **CISD** (C) in the opposite direction. The **O** is the market Open.
- **Stop:** beyond the sweep extreme.
- **Target:** the opposing liquidity.

## 2. How each rule was coded
| Rule | Exact definition used |
|---|---|
| Liquidity levels | Asia high/low (18:00–24:00 ET); London high/low (02:00–05:00); full overnight high/low (18:00–09:29); prior-day RTH high/low; 15-min fractal swing highs/lows (2 bars each side) formed overnight. A level counts only if it was still untouched at 09:29. |
| Sweep | The first 1-min bar between 09:30 and 10:30 that trades through a valid level. A swept low gives a long setup, a swept high gives a short setup. |
| CISD | A 1-min close beyond the **open of the run of consecutive opposite-colour candles** that delivered price into the sweep extreme. |
| IFVG | Optional filter: a 3-candle fair value gap formed inside that leg, closed through by the trigger bar. Tested both with and without it. |
| Entry | **Open of the next bar** after the CISD close. No look-ahead. |
| Stop | Sweep extreme ± 1 tick. |
| Target (4 versions) | (a) Nearest opposing marked liquidity at least 1R away. (b) The extreme of the move from 09:30 into the sweep. (c) Fixed 2R. (d) Fixed 3R. |
| Exit | Stop or target; otherwise flat at 15:59 ET. |
| Frequency | Maximum one trade per day: the first valid setup. |
| Minimum stop | Tested with no minimum, and with a minimum stop of 1× ATR(14). |
| Costs | max(2.25 pts scaled to price, 0.75 pt) per round trip. If stop and target are both hit inside the same bar, it is counted as a **loss** (conservative). |

That is 4 targets × IFVG on/off × 2 minimum-stop settings = **32 versions**.

## 3. Data
- **2010–2019:** CME **NQ** futures, 1-minute bars (Databento), continuous front month (highest-volume contract).
- **2020 – Oct 2026:** CME **MNQ** futures, 1-minute bars (Databento).
- About 4,100 trading days in total. Trading times are New York time, with daylight-saving adjustments.

## 4. Results — best version (target = opposing liquidity, IFVG required)
| Period | Trades | Trades / yr | Win rate | Planned R:R | Avg R / trade | Total R | Max drawdown |
|---|---|---|---|---|---|---|---|
| 2010–2019 | 1,787 | ~187 | 34.8% | 1 : 2.0 | −0.09R | **−166R** | 182R |
| 2020–2023 | 837 | ~210 | 32.9% | 1 : 2.1 | −0.05R | **−43R** | 83R |
| 2024–2026 | 558 | ~202 | 36.6% | 1 : 2.1 | −0.01R | **−3R** | 33R |
| **All 16 years** | **3,182** | **~200** | **34.6%** | **1 : 2.0** | **−0.07R** | **−212R** | — |

**Profitable years: 4 of 17.**

**Before costs:** +0.011R per trade (2010–19) and +0.027R per trade (2020–26). The setup has no raw edge. A 35% win rate at 1:2 is almost exactly breakeven, so costs make it negative.

### By year (same version)
| Year | Trades | Win rate | Total R | Median stop (pts) |
|---|---|---|---|---|
| 2010 | 91 | 41.8% | +0.3 | 5.8 |
| 2011 | 180 | 33.9% | −11.6 | 6.0 |
| 2012 | 179 | 30.2% | −42.9 | 6.0 |
| 2013 | 179 | 37.4% | −14.2 | 5.8 |
| 2014 | 186 | 30.1% | −42.8 | 7.4 |
| 2015 | 190 | 30.0% | −35.8 | 9.8 |
| 2016 | 195 | 34.9% | −8.2 | 8.3 |
| 2017 | 186 | 41.9% | +6.7 | 8.3 |
| 2018 | 206 | 34.5% | −7.7 | 16.4 |
| 2019 | 195 | 36.9% | −9.8 | 15.5 |
| 2020 | 206 | 35.4% | +12.2 | 29.6 |
| 2021 | 216 | 33.3% | −17.0 | 32.5 |
| 2022 | 209 | 31.1% | −30.1 | 50.3 |
| 2023 | 206 | 31.6% | −8.2 | 33.5 |
| 2024 | 205 | 38.0% | +17.9 | 39.8 |
| 2025 | 200 | 33.0% | −12.6 | 51.4 |
| 2026 (to Oct) | 153 | 39.2% | −8.3 | 75.5 |

## 5. All versions (2010–2026 combined)
| Target | IFVG filter | Trades | Avg R / trade | Profitable years |
|---|---|---|---|---|
| Opposing liquidity | yes | 3,182 | −0.07 | 4 / 17 |
| Opposing liquidity | no | 3,341 | −0.11 | 3 / 17 |
| Move extreme from 09:30 | yes | 2,491 | −0.09 | 2 / 17 |
| Move extreme from 09:30 | no | 2,885 | −0.13 | 2 / 17 |
| Fixed 2R | yes | 3,320 | −0.09 | 3 / 17 |
| Fixed 2R | no | 3,462 | −0.14 | 2 / 17 |
| Fixed 3R | yes | 3,320 | −0.10 | 2 / 17 |
| Fixed 3R | no | 3,462 | −0.15 | 1 / 17 |

The rows above use no minimum stop. Adding a minimum stop of 1× ATR changes the results by less than 0.01R per trade.
**Not one version is positive over the full sample.** The IFVG filter helps a little (−0.04R per trade) but does not flip the sign.

## 6. What this does and does not prove
- **It proves:** the *mechanical* LICO rules shown in the video have no statistical edge on NQ over 16 years and 3,000+ setups, before or after costs.
- **It does not test:** discretionary judgement, such as choosing which liquidity level "matters more" or skipping setups that "don't look right". That cannot be backtested. It also means the performance comes from the trader's discretion, not from the model.
- **One chart in a video is a single, selected example.** Across thousands of real occurrences, the same pattern performs like a random entry with a 1:2 bracket.

## 7. Open invitation
If any rule above differs from how you trade LICO, send the exact definition. For example: which levels count, the exact CISD reference candle, the IFVG size threshold, the entry type, any filters. I will re-run the full 16 years with your definitions and share the numbers either way.

---
*Code: `lico.py` (Python, fully reproducible). The full results grid is in `lico_grid.csv`.*
