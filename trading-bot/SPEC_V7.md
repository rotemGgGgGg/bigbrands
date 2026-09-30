# SP Model v7 — spec as implemented, and how it differs from v6

Files: `pine/sp_model_v7.pine` (strategy) · `backtest/sp_v7.py` (backtester). Both written from scratch,
same step order per bar. v6 files are kept unchanged for reference.

## Spec as implemented

**Sessions.** London range 00:00–06:00 NY. Sweeps count from 06:00 (the range is still forming before).
**Trigger timing (trader, v7.1):** the second trigger candle must close at or after 09:30 (earliest: the 09:25 bar).
A trigger completing earlier is void and never arms. Limits can only work between 09:30 and 14:00. Flat at 14:00.

**Sweep.** Wick is enough; exact touch counts (`high >= London high`). Each level is consumed once. After the
sweep the reference is the running extreme since the sweep; crossing the old London level again is not a sweep.

**Trigger.** Two consecutive candles on the same day; the sweep candle may be the first. Doji counts as both
bullish and bearish. No body minimum.

**Scenarios** (not restated in the v7 spec — carried over from the trader's earlier confirmations):
- S1: one side swept *inside* 09:30–14:00, other side not swept. Trigger against the sweep. 1.0 = extreme since the sweep.
- S2: continuation. After an in-window sweep: opens when S1 breaks its 1.0; 1.0 = S1's anchor 0.
  After a pre-open sweep: reference = post-sweep extreme at the first two-candle pullback; opens when price
  breaks it; 1.0 = the pullback extreme between reference and break **[IMPL-confirm]**. Trigger in the continuation direction.
- S3: both sides swept (from 06:00). Direction against the second sweep. 1.0 = the first side's extreme. 0.5 only, no value area.
- Once both sides are swept, only S3 can arm.

**Fib.** 1.0 fixed when the setup arms. 0 = extreme counted forward from the 1.0 bar only. Before the fill the
limit moves with the fib as 0 extends; after the fill entry/stop/target are frozen.

**Value area** (S1/S2), fib leg from the 1.0 bar to now, 999 rows, 70 %, re-checked every bar from the trigger:
above 0.588 no trade · 0.5–0.588 → 0.588 · 0.41–0.5 → 0.5 · below 0.41 no trade.

**Invalidation.** 1.0 break (strictly beyond) → dead. 14:00 → dead. A new setup replaces an armed, unfilled one.
Nothing else ends a setup: no expiry, no touch rule.

**Limits.** 1 trade per day (a win therefore also ends the session). 0.5 → stop 0.702 / target 0.267 (1.15R);
0.588 → stop 0.816 / target 0.36 (1.00R).

## Every difference from v6

| # | Area | v6 | v7 | Moves trades? |
|---|---|---|---|---|
| 1 | Setup arming time | Both trigger candles inside 09:30–14:00 | v7.1: the second candle closes at or after 09:30 — the 09:25 bar may complete a trigger | Rarely vs v6 |
| 2 | Limit before fill | Anchors freeze on the first non-extending bar; limit placed only after the freeze and a value-area lock | Limit placed from the trigger bar and moved every bar with the fib | **Yes** — orders sit one bar earlier after each extension |
| 3 | Level choice | Locked once in band; relocked only after a re-anchor | Re-chosen every bar (0.5 ↔ 0.588 ↔ none) until the fill | Yes |
| 4 | VA floor | 0.412 | 0.41 | Rarely |
| 5 | Doji | Neither bullish nor bearish | Both | Yes (triggers, S2 pullback reference) |
| 6 | Sweep touch | Strictly beyond the level | Exact touch counts | Rarely |
| 7 | "Entry touched, no fill" | Kills the setup | Removed. The setup lives on | Yes |
| 8 | Both sides swept while S1/S2 armed | S1/S2 cancelled immediately | S1/S2 stays until an S3 trigger replaces it, a 1.0 break, or 14:00 | Rarely |
| 9 | Replacement | One setup at a time; new triggers ignored | A new setup (different scenario, direction or 1.0) replaces an armed, unfilled one | Rarely (0 blocked triggers in v6's sample) |
| 10 | Re-trigger after a death | Needed two fresh candles after the death bar | No restriction | Rarely |
| 11 | Max failed setups | 3 per day | Not in the spec — removed | Possibly |
| 12 | Weekly −3R days off, −5R risk cut, news days | On | Not in the spec — removed | Only after losing streaks |
| 13 | Expiry, leg-growth cap, leg filter | Inputs, off by default | Removed | No (were off) |
| 14 | Position size | Risk $ / stop distance, skip if < 1 contract | Fixed contracts (input, default 1) | Only v6's "< 1 contract" skips |
| 15 | Tick rounding (Python) | Ties to even | Ties up, like Pine | Could shift an entry by 1 tick |

Same 60 days of Yahoo NQ data: v6 = 12 trades, v7 = 17 trades (0 S1, 6 S2, 11 S3), +6.24R, 7.4/month.
9 entries identical; the rest differ mainly by entering earlier (items 1–2).

## [IMPL] — decisions the spec does not make

1. Sweeps only from 06:00 ("setups are tracked from 00:00" read as: the day's state starts at 00:00, the range forms until 06:00).
2. S1 still needs its sweep inside 09:30–14:00 (only S2/S3 were extended to pre-open sweeps).
3. Last limit placement at the 13:50 bar's close (so it can only fill before 14:00). "A limit may still be placed as late as 14:00" read as: works until 14:00.
4. A limit that would sit through the market at the bar close (sell limit below price, buy limit above) is not placed that bar; the setup stays alive.
5. 1.0 break = strictly beyond the 1.0 (touch is not a break).
6. After an S2 or S3 1.0 break, that scenario is done for the day (carried over from v6).
7. S2 after a pre-open sweep: 1.0 = pullback extreme between the reference and the break.
8. London range needs ≥ 60 of its 72 bars.
9. "Same setup" (not a replacement) = same scenario, direction and 1.0 price and bar.
10. Fixed position size.

## Questions for the trader

- Items 2, 3, 4 and 7 above change which trades happen; the others are edge cases.
- "Max 1 trade per day" and "a win ends the session" say the same thing. Does a **loss** allow a second trade?
