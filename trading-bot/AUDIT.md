# Audit — backtester (Python) and strategy (Pine), v6

Status: findings only. Nothing below has been fixed except the additions marked (added).

## Sep 3 S2 fill vs "drawn fib"

Not a state bug. Bar-by-bar trace (`backtest/dump_setup.py 2026-09-03`):
the limit equals the fib price of the current anchors on every bar. Model fib at fill:
1.0 = 29,426.25 (low of the first S2 trigger candle, 11:10), 0 = 29,544.00; 0.5 = 29,485.00.
TradingView filled at 29,487.25. The 29,240 on the chart is the 10:05 low (29,241.75) — the
swing low before S1 failed. Spec §6 defines S2's 1.0 as the trigger-candle wick, "not the swing".
The chart and the spec disagree on S2's anchor → trader decision.

## Findings

| # | Where | Finding | Effect | Intentional? |
|---|---|---|---|---|
| 1 | Pine | No plot of a1 / a0 — only entry/stop/target were drawn, so any fib on the chart was manual | Can't audit anchors visually | No → (added) Fib 1.0 / Fib 0 plots |
| 2 | Both | S2 fib 1.0 = trigger-candle wick (spec §6); trader's chart uses the swing low | Changes every S2 entry price | **Resolved:** trader confirmed the swing low (S1's anchor_0); spec §6 was wrong |
| 3 | Python | Open position at a day change is dropped without recording (Pine closes and records it) | 0 occurrences: every weekday has its 13:55 bar | No |
| 4 | Python | `entry` key not cleared on unlock | None: every read is guarded by `locked` | Harmless |
| 5 | Python | `pos.a0` keeps updating after fill (logging only) — `leg_exit` ≠ Pine's leg-at-lock | Log column only | No |
| 6 | Logic diff | Stop and target touched in the same bar: Python assumes stop (spec §10); Pine's emulator picks by bar path | Can flip a trade's result | Known |
| 7 | Logic diff | Weekly −3R days off, −5R risk cut and news days exist only in Pine | Can skip days / change size in Pine only | No |
| 8 | Logic diff | Swing-toggle pivots: Python strict >, Pine `ta.pivothigh` tie rules | Only with the toggle on (off) | Known |
| 9 | Pine | `s2WhyHi/Lo` not reset daily | Unused | Cosmetic |

## State persistence (per variable group)

- Day state (London range, sweeps, running extremes, S1/S2/S3 flags, S2 eligibility, counters): reset at 00:00 NY in both.
- Setup state (anchors, frozen/locked, lock level/entry, extending): reset when a setup arms; gated by `setupScen != 0`. Not reset at day change in Pine — intentional, the gate makes stale values unreachable.
- Re-anchor (new extreme before fill): unfreezes, unlocks, clears level/entry (Pine clears lockEntry; Python leaves `entry`, see #4), cancels the order the same bar. Entry is recomputed from the new anchors at the next lock. Verified on Sep 3 12:55 → 13:00.
- Fill: position copies anchors/level from the order's state at the previous close; bracket is fixed.
- Cross-day by design: equity/R stats, weekly R, days off, drawdown multiplier.

## Invariants (added, both files; Pine: "Stop on invariant breach" input)

fill at the limit or better (±1 tick) · limit = fib level of current anchors · stop/entry/target
on the correct sides · leg > 0 · a1 never moves after the trigger · a0 never moves while frozen.
Python: all configurations pass. Mutation tests confirm the checks fire for: stale entry after a
re-anchor, limit priced from old anchors, a1 drifting, stop/target swapped.

## Pine vs Python on identical data — pending

Needs the TradingView MNQ 5m chart export + v6 List of Trades for the same range.
