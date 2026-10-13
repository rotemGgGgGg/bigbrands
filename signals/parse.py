"""Turning the sender's message into an order.

The sender uses one fixed template, which is the best thing that could have
happened: a parser for a known shape can demand that shape and refuse
anything else, instead of hunting for numbers in free text and hoping.

    💸XAUUSD⬆️ [5m]

    🟢Buy  : 4084.84
    🎯Take Profit : 4118.99
    🚫Stop Loss : 4071.36

The direction is stated twice, as an arrow and as a word. That redundancy is
used rather than ignored: if the two ever disagree, the message is refused.
It is the one check that catches the sender making a mistake, as opposed to
the parser making one.

Everything here refuses rather than guesses. A refusal costs one missed
signal and names what was wrong. A wrong read opens a position in the wrong
direction, which is the whole risk being managed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict

NUM = r"(\d{1,5}(?:\.\d{1,3})?)"

# Gold, and only gold: anything else is a different instrument and a
# different position size, so it is refused rather than assumed.
SYMBOL = re.compile(r"\bXAU\s*/?\s*USD\b", re.I)

UP, DOWN = "⬆", "⬇"          # ⬆ ⬇, with or without the emoji selector

# Gold has traded between roughly $250 and $5,000 historically. A number
# outside this is not a gold price, it is a parse that went wrong.
PLAUSIBLE = (250.0, 20000.0)


@dataclass
class Signal:
    raw: str
    symbol: str | None = None
    side: str | None = None          # "buy" or "sell"
    entry: float | None = None
    stop: float | None = None
    targets: list[float] = field(default_factory=list)
    timeframe: str | None = None
    order: str | None = None          # "market", "stop" or "limit"
    problems: list[str] = field(default_factory=list)

    @property
    def tradeable(self) -> bool:
        """Every field present, agreeing, and plausible. Nothing less."""
        return (not self.problems and self.symbol is not None
                and self.side is not None and self.entry is not None
                and self.stop is not None and bool(self.targets))

    def as_dict(self) -> dict:
        return asdict(self)


def _price(label: str, text: str) -> float | None:
    """Reads one labelled price. The label must be followed by a separator,
    so a number belonging to the next line is never picked up instead."""
    m = re.search(rf"{label}\s*[:=]\s*{NUM}", text, re.I)
    return float(m.group(1)) if m else None


def _direction_from_arrow(text: str) -> str | None:
    up, down = UP in text, DOWN in text
    if up and down:
        return None
    if up:
        return "buy"
    if down:
        return "sell"
    return None


def _direction_from_word(text: str) -> str | None:
    buy = re.search(r"\bbuy\b", text, re.I) is not None
    sell = re.search(r"\bsell\b", text, re.I) is not None
    if buy and sell:
        return None
    if buy:
        return "buy"
    if sell:
        return "sell"
    return None


def parse(text: str) -> Signal:
    sig = Signal(raw=text)

    if SYMBOL.search(text):
        sig.symbol = "XAU_USD"
    else:
        sig.problems.append("not a gold signal")

    arrow = _direction_from_arrow(text)
    word = _direction_from_word(text)
    if arrow is None and word is None:
        sig.problems.append("no direction given")
    elif arrow is not None and word is not None and arrow != word:
        # The sender's own two statements contradict each other. Guessing
        # which one they meant is exactly the trade not worth taking.
        sig.problems.append(f"arrow says {arrow}, word says {word}")
    else:
        sig.side = arrow or word
        if arrow is None:
            sig.problems.append("direction from word only, no arrow")
        elif word is None:
            sig.problems.append("direction from arrow only, no word")

    # The entry is labelled with the direction itself in this template, and
    # sometimes with an order type after it: "Buy Stop" fills on a break up
    # through the level, "Buy Limit" on a pullback to it, and a bare "Buy"
    # is the price at the moment of sending.
    if sig.side is not None:
        m = re.search(rf"\b{sig.side}\s*(stop|limit)?\s*[:=]\s*{NUM}", text, re.I)
        if m:
            sig.order = (m.group(1) or "market").lower()
            sig.entry = float(m.group(2))
    if sig.entry is None:
        sig.problems.append("no entry price")

    sig.stop = _price(r"stop\s*loss", text)
    if sig.stop is None:
        # A position with no stop is an unbounded loss. There is no version
        # of this where the trade is taken anyway.
        sig.problems.append("no stop loss")

    target = _price(r"take\s*profit", text)
    if target is not None:
        sig.targets.append(target)
    else:
        sig.problems.append("no take profit")

    tf = re.search(r"\[\s*(\d+\s*[mhd])\s*\]", text, re.I)
    if tf:
        sig.timeframe = tf.group(1).replace(" ", "").lower()

    _sanity(sig)
    return sig


def _sanity(sig: Signal) -> None:
    """Catches a parse that read numbers and assembled nonsense.

    A buy whose stop sits above its entry is not a cautious trade, it is a
    misread message, and noticing it here is free.
    """
    for label, value in [("entry", sig.entry), ("stop", sig.stop)] + \
            [(f"target {i + 1}", t) for i, t in enumerate(sig.targets)]:
        if value is not None and not (PLAUSIBLE[0] <= value <= PLAUSIBLE[1]):
            sig.problems.append(f"{label} {value} is not a plausible gold price")

    if sig.entry is None or sig.side is None:
        return
    if sig.stop is not None:
        if sig.side == "buy" and sig.stop >= sig.entry:
            sig.problems.append(f"buy with stop {sig.stop} at or above entry {sig.entry}")
        if sig.side == "sell" and sig.stop <= sig.entry:
            sig.problems.append(f"sell with stop {sig.stop} at or below entry {sig.entry}")
    for t in sig.targets:
        if sig.side == "buy" and t <= sig.entry:
            sig.problems.append(f"buy target {t} at or below entry {sig.entry}")
        if sig.side == "sell" and t >= sig.entry:
            sig.problems.append(f"sell target {t} at or above entry {sig.entry}")


def risk_reward(sig: Signal) -> float | None:
    """How much is risked per unit of what is being chased.

    Worth knowing before the position is sized, and worth recording for
    every signal, because the question of whether this sender is worth
    following is mostly this number against how often the target is hit.
    """
    if not sig.tradeable:
        return None
    risk = abs(sig.entry - sig.stop)
    reward = abs(sig.targets[0] - sig.entry)
    return round(reward / risk, 2) if risk else None
