"""How big, and when to stop.

The size is the whole thing. The same signals at one lot and at a hundredth
of a lot are the same edge and two completely different outcomes, and the
account that got emptied before this was built was emptied by size, not by
being wrong about direction.

So the size is never chosen per trade. It is derived: a fixed fraction of the
balance is what may be lost if the stop is hit, and the distance to the stop
decides how many units that allows. A wide stop therefore buys fewer units
automatically, which is the opposite of how it feels in the moment.

Three limits sit on top, and each one exists because without it a bad run
ends the account rather than the day:

  * a cap on the loss allowed in one day
  * a cap on how many positions may be open at once
  * a floor under the stop distance, since a stop a few cents away is noise
    and converts the spread into a guaranteed loss
"""
from __future__ import annotations

from dataclasses import dataclass

# For XAU_USD one unit is one ounce, so a one dollar move is one dollar per
# unit. That makes the arithmetic below plain, and it is the only instrument
# this bot trades.
DOLLARS_PER_UNIT_PER_DOLLAR = 1.0


@dataclass
class Limits:
    risk_per_trade: float = 0.005     # half a percent of the balance
    max_daily_loss: float = 0.02      # two percent, then the day is over
    max_open: int = 2
    min_stop_dollars: float = 2.0
    max_units: int = 100              # one lot of gold, as a hard ceiling


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
         loss_today: float = 0.0) -> Decision:
    """Units to trade, or zero and the reason why not."""
    if balance <= 0:
        return Decision(0, "no balance")

    if open_positions >= limits.max_open:
        return Decision(0, f"already holding {open_positions} positions")

    if loss_today >= balance * limits.max_daily_loss:
        return Decision(0, f"daily loss cap reached "
                           f"(${loss_today:.2f} of ${balance * limits.max_daily_loss:.2f})")

    distance = abs(entry - stop)
    if distance < limits.min_stop_dollars:
        # A stop this tight is inside the noise, and the spread would make it
        # a loss on arrival.
        return Decision(0, f"stop only ${distance:.2f} away, under the "
                           f"${limits.min_stop_dollars:.2f} floor")

    risk_budget = balance * limits.risk_per_trade
    units = int(risk_budget / (distance * DOLLARS_PER_UNIT_PER_DOLLAR))
    if units < 1:
        return Decision(0, f"${risk_budget:.2f} of risk cannot buy one unit "
                           f"at a ${distance:.2f} stop")
    capped = min(units, limits.max_units)
    note = (f"${risk_budget:.2f} risk / ${distance:.2f} stop = {units} units"
            + (f", capped to {capped}" if capped < units else ""))

    # The sign is what makes it a sell, and getting it wrong is the one
    # mistake that doubles the loss instead of taking it.
    return Decision(capped if side == "buy" else -capped, note)
