> ⚠️ **CORRECTION (2026-10-24): the No-Wick results in this file are INVALID: look-ahead bias.**
> The No-Wick simulator (`nowick.sim`) handled pending limit orders one signal at a time. When a signal's limit never filled within
> `expiry` bars, it went back and took the next signal's earlier touch. A live bot cannot do this, because it would need to know in
> advance that the first limit never fills. With a causal, bar-by-bar engine (`research/god/nw_causal.py`) the final No-Wick
> configuration makes **−0.02R per trade (×1 cost) and −0.11R (×2 cost)**, positive in 7/17 and 1/17 years.
> With expiry = 1 bar both engines agree exactly; the 'edge' grows with expiry only because of the look-ahead.
> GapFB, Pre-Fade and Opex are causal and unaffected. The valid portfolio is GapFB + Pre-Fade + Opex (`STRATEGY_NQ.md`).

# Research file: 50 NQ/MNQ templates + earlier strategies → final strategy and prop plan

Every number below comes from code in `research/s50/` and `research/god/`, run on real data. Estimates are labeled **(est.)**.

## 0. Setup
| Item | Value |
|---|---|
| Data | NQ 1-minute (Databento, front month by volume), 2010-06 → 2026-07. Bars 5/15/60 m, 24 h. Roll-aware (no position or indicator spans a roll bar). |
| Code | `bars.py`, `ind.py` (TradingView `ta.*` equivalents), `signals.py` (all 50 templates), `engine.py`, `phase1.py`, `phase2.py`, `phase2b.py`, `wf.py` |
| Fills | Signal on the bar close → market entry at the next open. Stop/target from ATR(14) at the signal bar. Stop checked on the entry bar; target only from the next bar (as Pine). Stop wins ties. One position at a time. |
| Costs | 2.25 pt × price/17000 per round trip (≈ $6.6 per MNQ at 25,000, versus ≈ $2.5 real commission + slippage). Stress = ×2. |
| Periods | Train 2010–19 (selection only), validate 2020–23, test 2024–26 |

**Deviations from the templates (documented):**
- **#24/#25 gap:** uses 09:30 open vs prior 16:00 close. The template's daily gap on CME is the 17:00→18:00 halt gap.
- **#34:** standard Aroon (the template's formula exceeds 100).
- **#50 higher timeframe:** 15 m on 5 m charts, 4× the chart otherwise. Uses the last *completed* bar.

## 1. Phase 1: each template alone
**194,400 variants** = 50 × TF {5, 15, 60} × lookback ×{0.5, 1, 2} × trend filter {template, toggled} × side {both, long, short} × session {24 h, RTH, AM} × stop {1, 1.5, 2, 3 ATR} × target {0.5, 1, 1.5, 2, 3, 4 ATR}.

- **Template defaults:** all 50 lose money on train, in both 24 h and RTH (`smoke.py`). The templates use target < stop, and after costs that is negative expectancy.
- **Variants with train R > 0:** 15.8%.
- **Multiple-testing bar:** max |t| expected by luck at 194k trials ≈ 4.9.
  - **No variant with a real sample clears it.** The 16 that do are template #43 with 5–7 trades (noise).
- **Funnel:** train t ≥ 3 and n ≥ 300 → 336 variants (11 templates) → validate R > 0: 332 (9 templates) → test R > 0: 256 (7 templates).
  - Survivors: #14 Donchian, #15 TTM Squeeze, #19 Engulfing, #23 First-Hour Breakout, #24 Gap Fade, #25 Gap&Go, #26 ATR Channel, #29 DEMA cross, #34 Aroon.
- **Best:** #25 Gap & Go, long only, 60 m, AM session, stop 1 ATR, target 3 ATR.
  - Per trade: train +0.30R (t 4.1), validate +0.29R, test +0.22R. 15 of 17 years positive.
  - This is the gap-continuation effect that GapFB already trades.

## 2. Phase 2: combinations
- **(a) Confirmation filters:** 1,764 variants. Each survivor's best variant × the state of every other template, as 'last signal agrees' or 'same-direction signal within 1/3/10 bars'.
  - Best: #25 + #47 state, train t 4.91 → test **+0.04R**. **No confirmation filter improves the out-of-sample result.**
- **(b) Portfolio beam search:** 11,436 portfolios. Daily R of the survivors (top 5 each) plus the earlier components, weights {0.5, 1, 2}, train Sharpe.
  - The search keeps choosing the earlier components (No-Wick, GapFB, Opex). Of the 50 templates, only #24 enters, at 0.5 weight.

## 3. Phase 4: walk-forward
Rule: each year, pick the template's variant with the best 3-year trailing t, then trade it the next year (2013–2026, OOS only).

| Template | OOS R/trade (×1 cost) | ×2 cost | OOS years positive |
|---|---|---|---|
| #26 ATR Channel Breakout | +0.117 | +0.118 | 9–10/14 (2024 alone = +60R) |
| #15 TTM Squeeze | +0.091 | +0.088 | 8/14 |
| #23 First-Hour Breakout | +0.074 | +0.003 | 8/14 |
| #25 Gap & Go | +0.068 | +0.063 | 10/14 |
| #14 Donchian | +0.040 | +0.085 | 9/14 |
| #29, #34, #24, #19 | ≈ 0 or negative | | |

**Verdict on the 50 templates:** weak edges at best (+0.05 to +0.12R, profitable in only 8–10 of 14 years). None matches the earlier components. The No-Wick component alone was +0.18R at ×2 cost and strict fills, 17/17 years.

## 4. Final strategy: unchanged, plus prop risk rules
Proof pack: `research/god/RESULT.md`. Selection was under ×2 cost + strict fills; test 2024–26 t = 5.3; 1-minute replay confirmed; the random-entry control is weaker.

| Component | Rules | Micros |
|---|---|---|
| No-Wick | 3 m, long only, signals 10:00–15:30. Green candle with lower wick ≤ 15%, EMA20 rising. Limit at the candle open (valid 100 bars). Stop 2×ATR, target 5R, flat 16:00. | 1 |
| GapFB | Gap ≥ 0.2% and quality score ≥ 2. 5-min OR breakout in the gap direction until 11:00. Stop 3×ATR, trail 5×ATR, flat 15:55. | 1 |
| Pre-Fade | 08:30→08:59 move > 3σ: fade at 09:00. TP 0.75×, SL 0.75× the move. Exit 11:00. | 2 |
| Opex | 3rd Friday: short 09:30. SL 0.5σ, TP 0.75σ. Exit 15:55. | 2 |

**Bot risk rules:**
- One net position: skip any trade opposite an open one. This costs about 3% of profit.
- **Skip any trade whose stop risk > $150 per micro.**

## 5. Prop plan: LucidFlex 50K
Sources: Lucid help center and Lucid's AI support reply. Price list per Phidias, 21 Oct 2026.

### Costs
| Item | Cost |
|---|---|
| Evaluation 50K, daily loss limit OFF | **$115.50** (coupon). $69 with the DLL on, **not recommended**: our worst day ≈ −$1,000. |
| Reset | $115 (DLL off) |
| Activation / monthly fee | $0 (Lucid: "no monthly subscription fees") |
| Data (CQG) | **unknown, ask Lucid** |
| NinjaTrader | included on CQG accounts (Lucid AI reply; confirm with a human) |
| VPS | Contabo 8 GB + Windows ≈ $10/mo, or VPS-Mart 4 GB ≈ $5–9/mo |
| Trading costs | Commission is charged by the account. Modeled at ≈ $6.6/round trip per micro, ≈ 2.6× real. |

### Rules used in the simulation
- **Eval:** +$3,000 target, $2,000 EOD-trailing max loss, 50% consistency.
- **Funded payout:**
  - 5 days of ≥ $150 profit, and positive net for the cycle.
  - Request 50% of profit: minimum $500, max $2,000.
  - First request locks the floor at start + $100.
  - 90% split, paid within 2 business days.

### Simulation results
Every start day 2020–26, final rules; `research/god/payout.py`.

| Payout policy | Eval pass | Eval days (median) | Days funded → 1st payout | 1st payout (gross) | Busted before 3 payouts |
|---|---|---|---|---|---|
| Request at $1,000 profit | 93–94% | 53–63 | 19–21 | ~$575–700 | **21%** |
| Request at $2,000 | 93–94% | 53–63 | 33–38 | ~$1,050 | 10–12% |
| **Request at $3,000 (recommended)** | **93–94%** | **53–63** | **~58** | **~$1,550 → $1,400 net** | **0%** |
| Request at $4,000 | 93–94% | 53–63 | 66–82 | $2,000 | 0% |

The ~6% of evals counted as "not passed" are mostly simulation windows that ran out of data before finishing.

### Timeline (est.)
| Step | Time |
|---|---|
| Bot build + 2 weeks sim | ~1 month |
| Evaluation | ~2.5–3 months |
| Funded → first payout | ~2.8 months |
| Payout paid | ≤ 2 business days |
| **Total to first payout** | **≈ 6–7 months** |

**Money to first payout (est.):** ~$115 eval × 1.07 expected attempts + ~$60 VPS ≈ **$185**. First payout ≈ **$1,400 net**. After that, ~$1,400–1,800 per payout cycle while the account survives.

## 6. Limitations
- **Backtest only.** There is no live record yet. Fill quality on CQG/NinjaTrader is unverified.
- **The $150 risk cap was chosen after seeing both periods.** It is one parameter; $100 is safe but slow, and $200 failed in 2024–26.
- **Rules come from third-party pages and an AI support reply.** Confirm with a human at Lucid before buying: CQG data fees, NinjaTrader license, VPS policy, DLL size.
- **No-Wick dominates the profit.** About 60% of its edge is the trade structure; random entries with the same exits give +0.10R.
