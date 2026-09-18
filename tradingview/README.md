# NY 08:00–08:15 Zone Strategy — TradingView implementation of Spec V1.0

`ny_zone_strategy.pine` — Pine Script **v6** strategy for ES / NQ.

---

## 1. How to run it (non-negotiable)

| | |
|---|---|
| Chart timeframe | **1 minute**. Nothing else. |
| Symbol | ES1! / NQ1! (or MES/MNQ — then set the point-value override) |
| Session on chart | Regular session or ETH; ETH is recommended so Asia/London levels exist |
| Chart timezone | irrelevant — all logic uses `America/New_York` internally |

The whole entry sequence (retest → confirmation → reclaim → next candle) is defined
on 1M candles in spec §3/§6/§7. The 5M break and the Daily bias are pulled with
`request.security(..., lookahead_off)` on **closed** bars only, so the backtest does
not repaint. Run it on 5M and the script draws a red warning label and refuses to
trade — the numbers you would get there would be fiction.

---

## 2. What the spec says vs. what the code does

### Objectively coded (the spec was decidable)

| Spec | Implementation |
|---|---|
| §2 New York session only | `sessTrade` entry window, default 08:15–12:00 ET; forced flat 15:55 ET |
| §2/§11 Asia / London / NY / Daily / swing liquidity | tracked live, drawn, greyed out once swept |
| §4 08:00–08:15 zone (H/L/O/C) | built from the 1M bars inside `sessZone`, box drawn, open & close plotted |
| §5 step 1 Break = **body close** beyond the zone, not a wick | 5M close `bC > zH` / `bC < zL` |
| §5 step 2 Retest may wick deep and even close inside the zone | only a close beyond the **opposite** edge invalidates |
| §7 Reclaim → wait one more 1M candle → entry | `reclaimWait`, plus the next candle must close beyond the zone *and* in direction |
| §10 Swept = wick touch **or** close beyond | `high >= level` / `low <= level` |
| §12 1M and 5M FVG | 3-candle gap detection on both timeframes |
| §13 Equilibrium = 50 % of break-leg → retrace-leg | `(breakExt + retestExt) / 2`, plotted |
| §14 SL below/above the FVG + 1–2 pt buffer, else structure | `slMode = "FVG, else swing"`, `slBufferPts`, no trailing |
| §15 TP = nearest **unswept** liquidity, liquidity beats rigid RR | `f_nearestAbove/Below`, `tpMinRR` floor, `tpFallbackRR` |
| §15 full exit at TP, no partials | single `strategy.exit` |
| §18 max 2 trades per day | `maxTrades`, and a second trade requires a fresh setup — never a re-entry on the same one |
| §19 strategy and sizing separated | Layer A = §§8–12 of the file, Layer B = `f_positionSize` only |

### Proxies — the spec did **not** define these, I had to invent a number

Every one is an input marked `[PROXY]`. **These are assumptions, not your strategy.**

| Spec | Problem | Proxy in code | Default |
|---|---|---|---|
| §6 "1–2, sometimes 3 candles until it confirms" | no decidable rule | weighted confluence score (1M FVG, 5M FVG, 1M momentum candle, close beyond equilibrium, FVG near equilibrium) evaluated in a window after the retest | score ≥ 2 within 6 candles |
| §8 "large / fast / aggressive candle", no volume allowed | not measurable as written | body ≥ 1.6 × ATR(14) **and** body/range ≥ 0.60, plus the candle must open on the far side of the zone | on |
| §16 Daily bias "must still be defined" | undefined | 4 selectable models (prev-day close vs prev-day midpoint / vs prior close / daily EMA / prev-day sweep & reclaim) | prev-day close vs midpoint |
| §17 "chart looks like a barcode" | not measurable | ATR(14)/ATR(100) ≥ 0.85, plus min/max zone width | on |
| §9 "no sufficient reaction" at a swept level | undefined | price must not close back on the original side of the level within 10 candles, then the same confluence score must fire | on |

**Read this before you believe any equity curve:** change `biasMode` or `confMinScore`
and the result moves more than any of the rules you actually wrote down. Backtest each
proxy switched off as well as on. If the edge only exists at one specific proxy setting,
you have curve-fitted my guesses, not validated your strategy.

---

## 3. Layer B — Risk manager (spec §19)

Completely separate from signal generation. Input: entry + stop. Output: contracts.

```
riskModel = "Fixed contracts"   -> always N contracts
          = "Percent of equity" -> equity * riskPct% / (stop distance * point value)
          = "Fixed risk cash"   -> riskCash        / (stop distance * point value)
```

Point value defaults to the symbol's (`ES = 50`, `NQ = 20`, `MES = 5`, `MNQ = 2`).
Override it with `pointValIn` when TradingView's contract data is wrong.
`maxQty` caps the size; if the computed size falls below `minQty` **the signal is
skipped entirely** rather than taken undersized — a stop too wide for the account is
a no-trade, not a small trade.

Swapping account size therefore never touches strategy logic. That is the point of §19.

---

## 4. State machine

```
idle ──5M body close beyond zone──> broken ──price back into zone──> retest
                                       │                               │
                              (momentum break skips retest)     confluence score ≥ N
                                       └───────────────┐               │
                                                       ▼               ▼
                                                   confirmed ──close beyond zone──> reclaimed
                                                                                        │
                                                                     next 1M candle confirms
                                                                                        ▼
                                                                                   LONG / SHORT
```
Invalidation at any stage: a close beyond the **opposite** zone edge, or the
confirmation window expiring. The dashboard (top right) shows the live state,
the current confluence score, the bias, the ATR ratio and the trade counter.

---

## 5. Known gaps — deliberately not coded

1. **§8 momentum quality.** Candle size relative to ATR is a weak stand-in for what you
   read visually. Without volume or delta this will fire on news spikes you would skip.
2. **§11 "relevant highs/lows at the start/end of a trend".** Only pivot swings and
   session/daily levels are implemented. Trend-structure labelling (BOS/CHoCH) is not.
3. **§16 Daily bias.** All four models are placeholders. Define this properly — it is
   the single biggest open item in the spec.
4. **§17 "no clear direction".** Only the ATR-ratio filter exists.
5. **Fills.** `process_orders_on_close = true`, 1 tick slippage, 2.50 commission per
   contract per side. Stop and target are OCO on the same bar — if both the stop and
   the target are hit inside one 1M candle, TradingView assumes the **stop** fills.
   That is conservative, but it is why intrabar fill order is not resolvable here.

## 6. Suggested calibration order

1. `biasMode = "Off"`, momentum setup off, liquidity setup off, `confMinScore = 1`.
   That is the pure §5–§7 break & retest. Get a baseline on 1–2 years of ES 1M.
2. Raise `confMinScore` and watch trade count vs. expectancy.
3. Turn on each bias model one at a time.
4. Add the momentum setup (§8), then the liquidity setup (§9).
5. Only then tune SL/TP parameters.

Do it in that order or you will not know which change did what.
