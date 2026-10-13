"""Did the target come before the stop?

That one question decides everything. The sender's risk-to-reward sits near
2.5, so he only needs to be right about 29% of the time to break even. Nobody
knows which side of that line he is on, including him, and guessing it with
money is what this is here to avoid.

So each signal is replayed against the minute bars that followed it, and the
first level touched is recorded. No money, no broker, no account.

Two honesties are built in rather than hidden:

  * A minute bar has a high and a low but no order. When one bar's range
    covers BOTH the target and the stop, which came first is unknowable from
    this data, and that is recorded as ambiguous instead of being guessed.
    With a thirteen dollar stop this will not be rare, and a win rate that
    quietly resolved those its own way would be worth nothing.

  * Futures prices sit above spot by more than one of these stops. When the
    series is futures, levels are measured as DISTANCES from the entry rather
    than as absolute prices, so the premium cancels. It is still an
    approximation, and it says so.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from parse import Signal, risk_reward
from prices import Series

SCHEMA = """
CREATE TABLE IF NOT EXISTS signals (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    received   INTEGER NOT NULL,      -- unix seconds the message arrived
    side       TEXT NOT NULL,
    entry      REAL NOT NULL,
    stop       REAL NOT NULL,
    target     REAL NOT NULL,
    risk       REAL NOT NULL,
    rr         REAL,
    timeframe  TEXT,
    raw        TEXT NOT NULL,
    -- filled in once the following minutes are known
    outcome    TEXT,                  -- win | loss | ambiguous | open
    minutes    INTEGER,               -- how long it took to resolve
    basis      TEXT                   -- spot | futures, so a result can be weighed
);
CREATE INDEX IF NOT EXISTS idx_signals_received ON signals (received);
"""


def connect(path: str) -> sqlite3.Connection:
    db = sqlite3.connect(path)
    db.executescript(SCHEMA)
    return db


def record(db: sqlite3.Connection, sig: Signal, received: int) -> int:
    """Stores a parsed signal before its outcome is known."""
    cur = db.execute(
        """INSERT INTO signals
             (received, side, entry, stop, target, risk, rr, timeframe, raw, outcome)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'open')""",
        (received, sig.side, sig.entry, sig.stop, sig.targets[0],
         abs(sig.entry - sig.stop), risk_reward(sig), sig.timeframe, sig.raw),
    )
    db.commit()
    return cur.lastrowid


@dataclass
class Resolution:
    outcome: str          # win | loss | ambiguous | open
    minutes: int | None
    note: str = ""


def resolve(side: str, entry: float, stop: float, target: float,
            received: int, series: Series) -> Resolution:
    """Walks forward from the signal and reports the first level touched."""
    bars = [b for b in series.bars if b.ts >= received]
    if not bars:
        return Resolution("open", None, "no price data after the signal yet")

    # Futures sit above spot by more than one stop, so the levels are rebuilt
    # as distances from the entry, anchored to where the series actually was.
    if series.is_spot:
        stop_at, target_at = stop, target
    else:
        anchor = (bars[0].high + bars[0].low) / 2
        stop_at = anchor + (stop - entry)
        target_at = anchor + (target - entry)

    for b in bars:
        if side == "buy":
            hit_target, hit_stop = b.high >= target_at, b.low <= stop_at
        else:
            hit_target, hit_stop = b.low <= target_at, b.high >= stop_at
        if hit_target and hit_stop:
            # Both inside one minute. Which came first is not in this data.
            return Resolution("ambiguous", (b.ts - received) // 60,
                              "target and stop both touched inside one minute")
        if hit_target:
            return Resolution("win", (b.ts - received) // 60)
        if hit_stop:
            return Resolution("loss", (b.ts - received) // 60)

    return Resolution("open", None, "neither level touched yet")


def update(db: sqlite3.Connection, series: Series) -> int:
    """Resolves every signal still open against the latest prices."""
    rows = db.execute(
        "SELECT id, side, entry, stop, target, received FROM signals "
        "WHERE outcome = 'open' OR outcome IS NULL").fetchall()
    settled = 0
    for sid, side, entry, stop, target, received in rows:
        r = resolve(side, entry, stop, target, received, series)
        if r.outcome == "open":
            continue
        db.execute("UPDATE signals SET outcome = ?, minutes = ?, basis = ? WHERE id = ?",
                   (r.outcome, r.minutes, series.source, sid))
        settled += 1
    db.commit()
    return settled


def report(db: sqlite3.Connection) -> str:
    rows = db.execute(
        "SELECT outcome, COUNT(*), AVG(minutes), AVG(rr) FROM signals GROUP BY outcome"
    ).fetchall()
    counts = {o: (n, m, rr) for o, n, m, rr in rows}
    wins = counts.get("win", (0, 0, 0))[0]
    losses = counts.get("loss", (0, 0, 0))[0]
    amb = counts.get("ambiguous", (0, 0, 0))[0]
    open_ = counts.get("open", (0, 0, 0))[0]
    settled = wins + losses

    lines = [f"signals recorded: {wins + losses + amb + open_}",
             f"  wins {wins} | losses {losses} | ambiguous {amb} | still open {open_}"]
    if settled:
        rr_row = db.execute(
            "SELECT AVG(rr) FROM signals WHERE outcome IN ('win','loss')").fetchone()
        rr = rr_row[0] or 0
        win_rate = wins / settled
        breakeven = 1 / (1 + rr) if rr else None
        lines.append(f"  win rate {100 * win_rate:.1f}% on {settled} settled")
        if breakeven is not None:
            lines.append(f"  average R:R {rr:.2f} needs {100 * breakeven:.1f}% to break even")
            verdict = "ahead of breakeven" if win_rate > breakeven else "behind breakeven"
            lines.append(f"  -> {verdict}")
    if amb:
        lines.append(f"  {amb} could not be settled from minute bars; a win rate "
                     f"that resolved those by guessing would not be worth reading")
    basis = db.execute("SELECT DISTINCT basis FROM signals "
                       "WHERE basis IS NOT NULL").fetchall()
    if any(b[0] == "futures" for b in basis):
        lines.append("  some results came from futures prices, measured as distance "
                     "from entry; close, not exact")
    return "\n".join(lines)
