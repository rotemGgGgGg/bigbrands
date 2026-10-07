# SP Model — everything we know (working file for Claude)

Purpose: one place for every rule, every trader answer, every labelled day and every decision, so the code
can be rewritten from this file alone and checked against the trader's own verdicts. Newest rule wins.
Sources: the original spec (SP_MODEL_BOT_SPEC.md), the trader's corrections relayed in this project (quoted
where possible), SPEC_V7.md. Status tags: **[T]** trader-confirmed · **[IMPL]** our decision, not confirmed ·
**[OPEN]** waiting for the trader · **[DEAD]** superseded, never bring back.

---

## 1. Vocabulary

| Term | Meaning |
|---|---|
| London range | high / low of 00:00–06:00 New York time |
| Sweep | a wick reaching the London level (touch counts) |
| Trigger | two consecutive same-colour 5-minute candles |
| fib 1.0 / a1 | where the move started — frozen once the setup arms |
| fib 0 / a0 | where the move got to — extends until the fill |
| VA ratio | VAH (short) / VAL (long) of the fib-leg volume profile, as a fib ratio |
| Round (S2) | one "break" that makes S2 available; a new break = a new round |
| Setup | armed fib; ends on a 1.0 break, 14:00, replacement, or the fill |

## 2. The rules as they stand (v7.5)

### Time
- **[T]** London range 00:00–06:00 NY. Entries 09:30–14:00. Flat at 14:00. Setups are tracked from 00:00.
- **[T]** Sweeps count from 06:00 at any time (pre-open included) and consume their level.
- **[T]** Trigger: the **second candle must close at or after 09:30** (the 09:25 bar is the earliest second
  candle). An earlier trigger is void forever — "a setup armed at 08:15 carrying its anchor into 09:45 is not
  something he does".
- **[IMPL]** Last limit placement at the 13:50 close.

### Sweep
- **[T]** Wick is enough; exact touch counts. A consumed level is dead; after the sweep the reference is the
  new extreme made during/after the sweep. Crossing the old level again is not a sweep.

### Trigger
- **[T]** Consecutive, the sweep candle can be the first, **doji counts both ways**, no body minimum.
- **[T]** It is a trigger, not a state: later colours don't matter.

### Scenarios
| | Condition | Direction | fib 1.0 | VA |
|---|---|---|---|---|
| S1 SHORT | London high swept **inside 09:30–14:00** [IMPL for the window], low not swept | two bearish → short | **[T]** highest point since the sweep | yes |
| S1 LONG | London low swept inside the window, high not | two bullish → long | **[T]** low of the first bullish trigger candle | yes |
| S2 LONG | high side, S2 round live | two bullish → long | **[T]** low of the first trigger candle | yes |
| S2 SHORT | low side, S2 round live | two bearish → short | **[T]** high of the first trigger candle | yes |
| S3 | both London levels swept (from 06:00, any time) | against the second sweep | **[T]** first sweep's extreme; 0 = second sweep's extreme | **no**, 0.5 only |

- **[T]** The moment both sides are swept it is S3 only.
- **[T]** "First trigger candle" = the first of the two, even if the second is the one that broke the level.

### S2 rounds (how S2 becomes available)
- **[T]** Opens when S1 on that side breaks its 1.0 (in-window sweep) — the level broken is S1's 1.0.
- **[T]** After a **pre-open** sweep: reference = post-sweep extreme at the **first two-candle pullback**
  ("the trader confirms the post-sweep extreme is set by a two-candle pullback, not any pullback");
  a wick beyond it opens S2.
- **[T]** Every new swing break opens a new round with fresh anchors. Swing = **3 bars**, middle bar beyond both
  neighbours. "Don't widen it."
- **[T] v7.5** A round is **cancelled** if price wicks back through the level it broke before the trigger:
  "There is no reason to take a long there. We didn't break above any high." "A broken level that price has
  fallen back through is not a break any more."
- **[T by example] v7.5** After a cancellation, S2 waits for a break of the **highest swing high (lowest swing
  low) formed since the cancelled break** — Aug 12 "waits for 30,001.75". **[OPEN]** confirm this vs "latest swing".
- **[T] Oct 2** A **new S2 break before the fill is a new setup**: the armed setup on that side is dropped at the
  break. If the new round is then cancelled, nothing is left — no trade (Aug 18, Sep 29 were −1R each without this).
- **[T idea Oct 2, number OPEN]** …but only after a **real retrace**: if the deepest pullback of the waiting leg is
  below `new_after_retrace` (default 0.36) the new break is the **same setup** (its 0 just moves); that absorbed
  break must hold — price back through it kills the setup (Sep 29). Decisive days: Sep 3, Sep 14, Oct 2.
- **[T Oct 7]** S1 is valid after a **pre-open** sweep too, as long as the trigger's second candle closes ≥ 09:30
  (a setup formed before 09:30 is not entered). Our old [IMPL] "S1 only for in-window sweeps" is **[DEAD]**.
- **[T Oct 7]** S2 reference / swing breaks need a **5-minute close** beyond the level ("close above the highest
  point that was created before"), not a wick. Supersedes "all breaks are wick-based" for these breaks.
- **[T Oct 7] Oct 2 labelled:** the trade is S2 LONG @0.588, 1.0 31,190 / 0 31,282.75, entry 31,228.25, stop
  31,207, target 31,249.25 — the 10:15 close above 31,258 is a new setup (pullback 0.45 ≥ 0.36; 0.5 gives no trade).
- **[T Oct 7]** VA slack 0.02 on floor and ceiling (our 5-minute profile ≠ TradingView's FRVP to the tick).
- **[T Oct 7]** Once S2 opens on a side (price closed through the post-sweep high/low), S1 on that side is over.
- **[T Oct 7] Oct 6** trader's fib: 1.0 = 31,500.5 = start of the up-run (09:50), not the first candle of the last pair
  (10:00, 31,523). `s2_run_anchor` (default ON, confirmed): with it Oct 6 is a 0.588 long, stopped −1R; changes 8 trades, R worse.
- **[T by example Oct 7] Oct 5** a break is undone only by a 5-minute **close** back through it (12:25 wicked 2 ticks
  under 31,232 and killed the round). Trade: S2 LONG @0.5, 1.0 31,200.25 / 0 31,275, entry 31,237.75, stop 31,222.5,
  target 31,255 → target. Supersedes the wick-based v7.5 cancel.
- **[T by example Oct 7] Sep 22** the high made on the break bar itself is a swing: after the 12:05 round was cancelled,
  the 12:45 close above 30,935.25 (12:05 high) is the next break. Trade: S2 LONG @0.5 13:35 → target. 1.0 = start of the
  green run, 12:40 (30,895.5) — **[T Oct 7]** confirmed, same rule as Oct 6.
- **[OPEN] conflict** Oct 2 the trader calls the 09:30 touch of the pre-open leg (08:30 sweep → 09:05 top) valid.
  That contradicts the [T] rule "second trigger candle must close ≥ 09:30" and principle 2 (no pre-open anchors).
- **[IMPL] v7.4** One setup per round; after its 1.0 break wait for the next break.
- **[IMPL]** The trigger pair only has to END at or after the break bar.
- **[T]** All breaks are wick-based (sweep, reference, swing, 1.0).

### Fib
- **[T]** 0 counts forward from the 1.0 bar only.
- **[T]** Before the fill the limit moves with the fib as 0 extends ("he keeps dragging the fib; the 0.588 moves
  with it; the value area is re-checked against the new leg — it may no longer be in band").
- **[T]** After the fill entry / stop / target are frozen (no trailing). **[DEAD]** original spec's trailing stop.

### Value area
- **[T]** FRVP over the fib leg (from the 1.0 bar to now, price range a1..a0), 999 rows, 70 %, Volume Total.
- **[T]** Bands: above 0.588 → no trade · 0.51–0.588 → limit at 0.588 · 0.41–0.51 → limit at 0.5 (a VA sitting on 0.5 is a 0.5 entry — trader, Oct 2; tolerance 0.01 is ours) · below 0.41 → no
  trade. "0.25 and 0.70 are both explicit skips." Checked every bar from the trigger.
- Trader habit: "he drags the volume profile forward as the leg extends and takes the trade the first moment VAH
  lands on the entry level".

### Levels
- **[T]** 0.5 → stop 0.702, target 0.267 (1.15R). 0.588 → stop 0.816, target 0.36 (1.00R).
  0.298 / 0.618 unused.

### Invalidation and caps
- **[T]** 1.0 break → dead. 14:00 → dead. Replacement by a newer setup. **No expiry. Touching 0.5 without a
  fill does NOT kill a 0.588 setup.**
- **[T]** Max 1 trade per day; the first fill ends the day, win or lose.
- **[T]** 3 failed setups (1.0 breaks) end the session. Replacement / 14:00 are not failures.
- **[IMPL]** S3 dead for the day after its 1.0 break. 1.0 break = strictly beyond. Limit through the market not
  placed that bar. Second trigger candle beyond the first's extreme → no setup. London needs ≥ 60/72 bars.
  1 contract.

## 3. Superseded rules — do not reintroduce **[DEAD]**
- 30–150 point leg filter (circular measurement). Leg-growth cap (killed Feb 16). Setup expiry (12/24 bars).
- VA check as a rejection at trigger; locking the level choice once; freezing a0 at a "non-extending" bar.
- a0 counted from the sweep bar (it counts from the a1 bar).
- VA floor 0.412 (it is 0.41). Doji = neither.
- S2 needs S1 to fail first (pre-open sweeps open S2 through the reference). S2 1.0 = S1's a0 (replaced by the
  first trigger candle). Pre-open S2 anchor carried into the session.
- "Touch of the entry without fill kills the setup". Weekly −3R stop, risk cuts, news days, risk-based sizing.
- Close-based S2 break.

## 4. How the trader thinks (principles to judge a day by)
1. **A break has to hold.** If price came back through the level, nothing was broken (Aug 12).
2. **Anchors are fresh.** The fib is drawn from the trigger candles he sees in the session, never from a
   pre-open setup (Aug 10, v7.1).
3. **Short-lived setups.** Real benchmark Feb 16: trigger → lock 4 bars, lock → fill 2 bars, leg grew 2.2×.
   A 21-bar-old setup whose leg grew 3.6× "is a different trade" (Sep 3, v6).
4. **The VA decides.** Out of band = no trade, even on a perfect-looking retrace (Sep 8).
5. **About 9 trades a month** on MNQ.
6. Rule fidelity over P&L: "If a change follows the trader's rules and makes R worse, keep it."

## 5. Labelled days (ground truth)

| Day | Trader verdict | Source | v7.5 (Yahoo) |
|---|---|---|---|
| 2026-02-16 | **Trade**: S1 LONG, 1.0 24,692.5, 0 24,797.5, leg 105, VAL ratio 0.538 → 0.588 entry 24,735.75, stop 24,711.75, target 24,760 | trader chart | not in data |
| 2026-09-08 | **No trade** (re-anchor pushed VA out of band) | trader | no trade ✓ |
| 2026-09-03 | v6 13:10 S2 fill "not a trade the model would take" | trader | 13:00 S2 LONG −1R — **to check** |
| 2026-08-10 | **No trade** (confirmed v7.1, v7.2, and again on the v7.4 13:05 short) | trader chart | no trade ✓ |
| 2026-08-12 | **No trade** — "we didn't break above any high" | trader | no trade ✓ |
| two more days | "three days that aren't right" — only Aug 10 was named | user | **[OPEN]** which days |

## 6. Engine facts (both codebases)
- Bar step order: fills → new day → London → sweeps → flat 14:00 → armed setup (1.0 break / 14:00 / a0) →
  S2 rounds → triggers → place/move limit.
- TradingView fill emulation: open → nearer extreme → other extreme → close; limit fills on touch; a gap fills at
  the open. Ticks round ties-up (math.round_to_mintick).
- Invariants: fill at the limit or better; bracket on the correct side; a1 never moves.
- Data: Yahoo NQ=F 60 days (5m) vs the user's MNQ1! in TradingView — a few ticks apart, 18/26 days identical in
  the last comparison. Bar-for-bar parity needs TradingView's own bars (the MCP can pull them once connected).
- Multi-year: NinjaTrader 8 minute export → backtest/run_years.py.

## 7. Version log (Yahoo NQ, Jul 22 – Sep 30)

| Version | Change | Trades | Total R |
|---|---|---|---|
| v7.3 | S2 re-triggers every swing break, 3-fail cap | 29 | +4.06 |
| v7.4 | one S2 setup per round | 30 | +3.33 |
| v7.5 latest-swing | cancelled break, wait for latest swing | 26 | +5.33 |
| **v7.5 (default)** | cancelled break, wait for highest swing | **18** (S2 7, S3 11) | **−1.08** |
| **v8** | full rewrite from this file (Side objects); Python v8 = v7.5 on trades, all events and the funnel | 18 | −1.08 |
| v8 + VA on 0.5 | VA up to 0.51 → 0.5 entry (trader, Oct 2) | 19 | +0.07 |
| **v8 + new break** | a new S2 break drops the waiting setup (trader, Oct 2) | **17** (9 wins) | **+2.07** |

## 8. Code
- `pine/sp_model_v8.pine` and `backtest/sp_v8.py` are the current versions (v7 files kept for reference).
- Python v8 reproduces v7.5 exactly (18 trades / 500 events, and 26 / 1,172 with the latest-swing variant).
- Pine v8 is not compiled yet — the user compiles it in TradingView.

## 9. Trader-style review of the 18 v7.5 trades
- Every S2 trade follows a break that held until its trigger (the v7.5 rule does this by construction).
- Dropping IMPL 9 (self-break on the trigger) brings back an Aug 10 11:50 short — the trader said Aug 10 has no
  trade, so IMPL 9 agrees with a labelled day.
- Sep 3 13:00 S2 LONG is a different setup from the rejected v6 one (trigger 12:40, 4 bars to fill, leg ×1.2) —
  consistent with the rules, needs his verdict.
- S3 setups live long: Sep 28 (23 bars, leg ×1.6), Aug 6 (22 bars). Allowed ("no expiry") but unlike the Feb 16
  benchmark — worth showing him.
- Pace: 18 trades in 2.3 months = 7.8/month vs his ~9/month.
- S1 produces 0 trades: 7 S1 LONG triggers die on IMPL 9, the rest on 14:00 or a 1.0 break.

## 10. Open questions for the trader
1. After a cancelled break: wait for the highest swing since the break, or any newer (lower) swing?
2. Does a **loss** allow a second trade? (Stated: "the first fill ends the day, win or lose" — treated as yes-ends.)
3. Which are the other two "not right" days?
4. [IMPL] items that move trades: S1 window, limit through the market, trigger pair ending at/after the break,
   same-scenario trigger keeps the first anchor, self-break on the trigger.
5. The cancellation check before the trigger — also on the break bar itself? (we skip it)
