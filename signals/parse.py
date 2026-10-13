"""Turning a person's message into an order.

This is the part that breaks. A signal is written for a human: the direction
may be a word or an arrow, the entry may be a price, a range, or "market",
and the targets may be numbered, listed, or absent. Nothing guarantees the
sender is consistent, and a message that is misread does not fail loudly —
it opens the wrong trade.

So the parser is deliberately strict. It extracts only what it can name with
confidence and refuses the rest, because a refusal costs one missed signal
and a wrong guess costs a position. Every refusal says what was missing, so
the format it could not read can be added on purpose rather than by luck.

The patterns below are a first pass written before seeing the real messages.
They are meant to be corrected against them, not trusted.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict

# Gold goes by several names depending on the broker and the writer.
GOLD = r"(?:XAU\s*/?\s*USD|XAUUSD|GOLD|ZAHAV|זהב)"

NUM = r"(\d{1,5}(?:[.,]\d{1,3})?)"


@dataclass
class Signal:
    raw: str
    symbol: str | None = None
    side: str | None = None           # "buy" or "sell"
    order_type: str | None = None     # "market" or "limit"
    entry: float | None = None
    entry_high: float | None = None   # when the sender gives a zone
    stop: float | None = None
    targets: list[float] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    @property
    def tradeable(self) -> bool:
        """Only a signal with a direction, an entry and a stop may be sent on.

        A trade without a stop is an unbounded loss, and this exists because
        an unbounded loss already happened once.
        """
        return not self.problems and self.side is not None and self.stop is not None

    def as_dict(self) -> dict:
        return asdict(self)


def _num(text: str) -> float | None:
    try:
        return float(text.replace(",", "."))
    except (TypeError, ValueError):
        return None


def _find_side(text: str) -> str | None:
    # Word boundaries matter: "sell" must not be found inside another word,
    # and a message can mention the opposite direction while describing it.
    if re.search(r"\b(buy|long|bullish|קונים|לונג)\b", text, re.I):
        buy = True
    else:
        buy = False
    if re.search(r"\b(sell|short|bearish|מוכרים|שורט)\b", text, re.I):
        sell = True
    else:
        sell = False
    if buy and sell:
        return None          # ambiguous; the caller records it as a problem
    if buy:
        return "buy"
    if sell:
        return "sell"
    return None


def parse(text: str) -> Signal:
    sig = Signal(raw=text)
    flat = text.replace("–", "-").replace("—", "-")

    if re.search(GOLD, flat, re.I):
        sig.symbol = "XAU_USD"
    else:
        sig.problems.append("no instrument named")

    sig.side = _find_side(flat)
    if sig.side is None:
        sig.problems.append("direction unclear")

    # Entry: a zone first, since a zone also matches the single-price pattern.
    zone = re.search(rf"(?:entry|@|at|כניסה)\D{{0,12}}{NUM}\s*-\s*{NUM}", flat, re.I)
    if zone:
        lo, hi = _num(zone.group(1)), _num(zone.group(2))
        sig.entry, sig.entry_high = min(lo, hi), max(lo, hi)
        sig.order_type = "limit"
    else:
        single = re.search(rf"(?:entry|@|at|כניסה)\D{{0,12}}{NUM}", flat, re.I)
        if single:
            sig.entry = _num(single.group(1))
            sig.order_type = "limit"
        elif re.search(r"\b(market|now|cmp|מיד|עכשיו)\b", flat, re.I):
            sig.order_type = "market"
        else:
            sig.problems.append("no entry found")

    stop = re.search(rf"(?:sl|stop[\s-]?loss|stop|סטופ)\D{{0,12}}{NUM}", flat, re.I)
    if stop:
        sig.stop = _num(stop.group(1))
    else:
        sig.problems.append("no stop loss found")

    # Targets, however the sender numbers them. The index in "TP1" has to be
    # told apart from the price in "TP 4125", so an index is only an index
    # when something separates it from what follows.
    label = r"(?:tp|target|take[\s-]?profit|מטרה)"
    index = r"(?:\s*\d{1,2}(?=\s*[:=.)\-]|\s))?"
    for m in re.finditer(rf"{label}{index}\s*[:=.)\-]?\s*{NUM}", flat, re.I):
        value = _num(m.group(1))
        if value is not None and value not in sig.targets:
            sig.targets.append(value)
    if not sig.targets:
        sig.problems.append("no target found")

    _sanity(sig)
    return sig


def _sanity(sig: Signal) -> None:
    """Catches a parse that read numbers but assembled nonsense.

    A buy whose stop sits above its entry is not a cautious trade, it is a
    misread message, and it is cheaper to notice that here.
    """
    if sig.entry is None or sig.stop is None or sig.side is None:
        return
    if sig.side == "buy" and sig.stop >= sig.entry:
        sig.problems.append(f"buy with stop {sig.stop} at or above entry {sig.entry}")
    if sig.side == "sell" and sig.stop <= sig.entry:
        sig.problems.append(f"sell with stop {sig.stop} at or below entry {sig.entry}")
    for t in sig.targets:
        if sig.side == "buy" and t <= sig.entry:
            sig.problems.append(f"buy target {t} at or below entry {sig.entry}")
        if sig.side == "sell" and t >= sig.entry:
            sig.problems.append(f"sell target {t} at or above entry {sig.entry}")
    # Gold trades in the low thousands; a number far outside that is a price
    # read out of some other sentence.
    prices = [("entry", sig.entry), ("stop", sig.stop)]
    prices += [(f"target {i + 1}", t) for i, t in enumerate(sig.targets)]
    for label, value in prices:
        if value is not None and not (500 <= value <= 20000):
            sig.problems.append(f"{label} {value} is not a plausible gold price")
