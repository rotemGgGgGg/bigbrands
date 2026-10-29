"""How big, and when to stop.

The size is the whole thing. The same signals at one lot and at a hundredth
of a lot are the same edge and two completely different outcomes, and the
account that got emptied before this was built was emptied by size, not by
being wrong about direction.

So the size is never chosen per trade. A fixed number of dollars is what may
be lost if the stop is hit, and the distance to the stop decides how many
ounces that allows. A wide stop therefore buys fewer ounces automatically,
which is the opposite of how it feels in the moment.

On a funded account the firm's own limits are the real boundary: cross the
daily loss or the total loss once and the account is gone, profitable or not.
So before any order, the bot asks a stricter question than the firm does: if
every open position AND this new one hit their stops right now, on top of
what is already lost today and overall, would it still be inside its own
caps? The caps sit below the firm's on purpose, because a stop can fill
worse than its price and a firm counts floating losses too.
"""
from __future__ import annotations

from dataclasses import dataclass

# For XAU_USD one unit is one ounce, so a one dollar move is one dollar per
# unit. That makes the arithmetic below plain, and it is the only instrument
# this bot trades.
DOLLARS_PER_UNIT_PER_DOLLAR = 1.0


@dataclass
class Limits:
    risk_usd: float | None = None     # fixed dollars per trade; wins over the fraction
    risk_per_trade: float = 0.005     # otherwise, a fraction of the balance
    daily_stop_usd: float | None = None   # stop for the day past this loss
    total_stop_usd: float | None = None   # stop for good past this drawdown
    max_open: int = 2
    max_trades_day: int | None = None  # new trades per broker day, then stop
    min_stop_dollars: float = 2.0
    max_units: int = 100              # one lot of gold, as a hard ceiling
    risk_max_usd: float | None = None # may round up to the nearer size, never past this
    max_daily_loss: float = 0.02      # fraction fallback when no dollar cap is set


@dataclass
class AccountState:
    """What the guard needs to know about the account right now. Losses are
    positive numbers; floating losses on open positions are included, as a
    funded account counts them."""
    balance: float
    equity: float | None = None
    day_loss: float = 0.0          # since the start of the broker's day
    total_loss: float = 0.0        # below the starting balance
    open_risk: float = 0.0         # what open positions lose if every stop fills
    open_count: int = 0
    trades_today: int = 0          # orders this bot placed since the day began


@dataclass
class Decision:
    units: int
    detail: str

    @property
    def allowed(self) -> bool:
        # A sell is a negative number of units, so this asks whether there is
        # a position at all, not whether it is a long one. Reading it as
        # "greater than zero" would have silently refused every sell.
        return self.units != 0


def size(balance: float, entry: float, stop: float, side: str,
         limits: Limits, open_positions: int = 0,
         loss_today: float = 0.0, state: AccountState | None = None) -> Decision:
    """Units to trade, or zero and the reason why not."""
    if state is not None:
        balance, open_positions, loss_today = state.balance, state.open_count, state.day_loss
    if balance <= 0:
        return Decision(0, "no balance")

    if (limits.max_trades_day is not None and state is not None
            and state.trades_today >= limits.max_trades_day):
        # A fail stop, not a forecast: the channel rarely sends this many in a
        # day, so a day that does is either a bad day or something misread.
        return Decision(0, f"day limit: {state.trades_today} trades already placed "
                           f"today, the most is {limits.max_trades_day}")

    if open_positions >= limits.max_open:
        return Decision(0, f"already holding {open_positions} positions")

    distance = abs(entry - stop)
    if distance < limits.min_stop_dollars:
        # A stop this tight is inside the noise, and the spread would make it
        # a loss on arrival.
        return Decision(0, f"stop only ${distance:.2f} away, under the "
                           f"${limits.min_stop_dollars:.2f} floor")

    risk_budget = limits.risk_usd if limits.risk_usd else balance * limits.risk_per_trade
    units = int(risk_budget / (distance * DOLLARS_PER_UNIT_PER_DOLLAR))
    # Ounces come whole, so the risk lands below the budget, sometimes well
    # below ($17.88 of $25 at a $8.94 stop). With a ceiling set, one ounce
    # more is taken when it lands nearer the budget and stays under the
    # ceiling; without one, the size only ever rounds down.
    if limits.risk_max_usd:
        up = units + 1
        if (up * distance <= limits.risk_max_usd
                and abs(up * distance - risk_budget) < abs(units * distance - risk_budget)):
            units = up
    if units < 1:
        return Decision(0, f"${risk_budget:.2f} of risk cannot buy one ounce "
                           f"at a ${distance:.2f} stop")
    units = min(units, limits.max_units)
    new_risk = units * distance

    # The caps, checked as if everything open and this trade all stop out.
    if limits.daily_stop_usd is not None and state is not None:
        worst_day = state.day_loss + state.open_risk + new_risk
        if worst_day > limits.daily_stop_usd:
            return Decision(0, f"daily cap: ${state.day_loss:.2f} lost today, "
                               f"${state.open_risk:.2f} open at risk, ${new_risk:.2f} more "
                               f"would reach ${worst_day:.2f} of ${limits.daily_stop_usd:.2f}")
    elif state is None and loss_today >= balance * limits.max_daily_loss:
        return Decision(0, f"daily loss cap reached "
                           f"(${loss_today:.2f} of ${balance * limits.max_daily_loss:.2f})")
    if limits.total_stop_usd is not None and state is not None:
        worst_total = state.total_loss + state.open_risk + new_risk
        if worst_total > limits.total_stop_usd:
            return Decision(0, f"total cap: ${state.total_loss:.2f} down overall, "
                               f"${state.open_risk:.2f} open at risk, ${new_risk:.2f} more "
                               f"would reach ${worst_total:.2f} of ${limits.total_stop_usd:.2f}")

    note = f"${risk_budget:.2f} risk / ${distance:.2f} stop = {units} oz"
    # The sign is what makes it a sell, and getting it wrong is the one
    # mistake that doubles the loss instead of taking it.
    return Decision(units if side == "buy" else -units, note)
