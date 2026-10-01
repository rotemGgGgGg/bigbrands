"""The bridge's brain: turn one TradingView alert into one decision per account.

No I/O here — the server feeds signals and the clock in, and gets back what to send. That keeps every rule testable.

Position and P&L are ESTIMATED from the TradingView alerts (entry price, exit price), not read from the broker.
They drive the prop guard rails; the broker's numbers are the truth.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import datetime, time
from zoneinfo import ZoneInfo

from .config import Account, point_value

NY = ZoneInfo("America/New_York")


@dataclass
class Signal:
    strategy: str
    symbol: str
    action: str                 # "buy" | "sell" (TradingView {{strategy.order.action}})
    contracts: float
    position: str               # "long" | "short" | "flat" (TradingView {{strategy.market_position}})
    price: float
    order_id: str = ""
    sl: float = 0.0             # optional bracket in points
    tp: float = 0.0

    @property
    def is_close(self) -> bool:
        return self.position == "flat"

    @property
    def side(self) -> str:
        return "buy" if self.action == "buy" else "sell"


@dataclass
class AccountState:
    position: int = 0           # signed contracts (estimate)
    entry_price: float = 0.0
    symbol: str = ""
    day: str = ""               # NY date the counters belong to
    realized_today: float = 0.0
    trades_today: int = 0
    balance: float = 0.0        # estimated closed P&L since start
    peak_eod: float = 0.0       # highest end-of-day balance (trailing drawdown anchor)

    def roll_day(self, today: str):
        if self.day != today:
            if self.day:
                self.peak_eod = max(self.peak_eod, self.balance)
            self.day, self.realized_today, self.trades_today = today, 0.0, 0

    def room(self, trailing_dd: float) -> float:
        return self.balance - (self.peak_eod - trailing_dd)


@dataclass
class Decision:
    account_id: str
    send: bool
    reason: str
    qty: int = 0
    payload: dict = field(default_factory=dict)


def _hm(s: str) -> time:
    h, m = s.split(":")
    return time(int(h), int(m))


def render(template: dict, values: dict) -> dict:
    """Replace "{{name}}" strings anywhere in the template. A string that is exactly one placeholder keeps the value's type."""
    def sub(x):
        if isinstance(x, dict):
            return {k: sub(v) for k, v in x.items()}
        if isinstance(x, list):
            return [sub(v) for v in x]
        if isinstance(x, str):
            for k, v in values.items():
                tag = "{{" + k + "}}"
                if x == tag:
                    return v
                if tag in x:
                    x = x.replace(tag, str(v))
        return x
    return sub(copy.deepcopy(template))


def decide(sig: Signal, acc: Account, st: AccountState, now: datetime, kill: bool) -> Decision:
    """What to do for one account. Mutates `st` only when the order will be sent."""
    st.roll_day(now.astimezone(NY).date().isoformat())
    r = acc.rules
    pv = point_value(sig.symbol)

    if sig.is_close:
        if st.position == 0:
            return Decision(acc.id, False, "already flat")
        qty = abs(st.position)
        payload = render(acc.template_close, dict(side=sig.side, qty=qty, symbol=sig.symbol, price=sig.price, time=now.isoformat()))
        if acc.enabled:                     # exits go out even with the kill switch on
            pnl = (sig.price - st.entry_price) * (1 if st.position > 0 else -1) * qty * pv
            st.realized_today += pnl
            st.balance += pnl
            st.position, st.entry_price = 0, 0.0
            return Decision(acc.id, True, f"close est {pnl:+.0f}$", qty, payload)
        return Decision(acc.id, False, "account disabled")

    # ── new entry: every guard must pass ──
    t = now.astimezone(NY).time()
    if kill:
        return Decision(acc.id, False, "kill switch on")
    if not acc.enabled:
        return Decision(acc.id, False, "account disabled")
    if not (_hm(r.entry_start) <= t < _hm(r.entry_end)):
        return Decision(acc.id, False, f"outside entry window {r.entry_start}-{r.entry_end} NY")
    if st.position != 0:
        return Decision(acc.id, False, "already in a position")
    if st.trades_today >= r.max_trades_per_day:
        return Decision(acc.id, False, f"max {r.max_trades_per_day} trades today")
    if st.realized_today <= -r.daily_loss_limit:
        return Decision(acc.id, False, f"daily loss limit {r.daily_loss_limit:.0f}$ hit")
    if r.profit_target and st.balance >= r.profit_target:
        return Decision(acc.id, False, "profit target reached")
    qty = min(max(1, round(sig.contracts * acc.multiplier)), r.max_contracts)
    room = st.room(r.trailing_dd)
    if sig.sl > 0 and qty * sig.sl * pv >= room - r.dd_buffer:
        return Decision(acc.id, False, f"stop would leave < {r.dd_buffer:.0f}$ to the drawdown (room {room:.0f}$)")
    if sig.sl <= 0 and room < r.dd_buffer:
        return Decision(acc.id, False, f"room to drawdown {room:.0f}$ < buffer")

    payload = render(acc.template_open, dict(side=sig.side, qty=qty, symbol=sig.symbol, price=sig.price, sl=sig.sl, tp=sig.tp,
                                             time=now.isoformat()))
    st.position = qty if sig.side == "buy" else -qty
    st.entry_price, st.symbol = sig.price, sig.symbol
    st.trades_today += 1
    return Decision(acc.id, True, "open", qty, payload)
