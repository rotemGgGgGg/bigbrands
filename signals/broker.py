"""Placing the order, or pretending to.

Two brokers behind one interface. The paper one writes down what it would
have done and touches no account; the live one sends it to OANDA. The bot
does not know which it has, so the path that gets tested is the path that
runs, and switching to money changes one setting rather than any code.

The OANDA details that matter, verified against their docs and endpoints
rather than remembered: units are signed, positive long and negative short;
a market order's timeInForce is FOK; the stop and target ride along with the
order as stopLossOnFill and takeProfitOnFill, so a filled position is never
briefly naked; and practice and live are different hostnames, both of which
answer 401 without a token.

For XAU_USD one unit is one ounce, so 100 units is the one lot that a
dollar-per-pip table assumes.
"""
from __future__ import annotations

import json
import sqlite3
import urllib.error
import urllib.request
from dataclasses import dataclass

PRACTICE = "https://api-fxpractice.oanda.com"
LIVE = "https://api-fxtrade.oanda.com"


@dataclass
class Fill:
    ok: bool
    detail: str
    order_id: str | None = None
    price: float | None = None


class OandaBroker:
    """Live or practice; the only difference is the hostname."""

    def __init__(self, token: str, account_id: str, practice: bool = True):
        self.base = PRACTICE if practice else LIVE
        self.account = account_id
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept-Datetime-Format": "UNIX",
        }
        self.practice = practice

    def _call(self, method: str, path: str, body: dict | None = None) -> dict:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(f"{self.base}{path}", data=data,
                                     headers=self.headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            # OANDA explains refusals in the body, and that explanation is
            # the whole value of the error — a bare status code would leave
            # a rejected order looking like a network problem.
            raw = e.read().decode(errors="replace")
            try:
                return {"__error__": json.loads(raw), "__status__": e.code}
            except ValueError:
                return {"__error__": raw[:400], "__status__": e.code}

    def summary(self) -> dict:
        return self._call("GET", f"/v3/accounts/{self.account}/summary")

    def tradeable(self, instrument: str = "XAU_USD") -> bool:
        """Whether this account may trade gold at all.

        OANDA's instrument list depends on the account's regulatory division,
        so this is a real question and not a formality.
        """
        got = self._call("GET", f"/v3/accounts/{self.account}/instruments"
                                f"?instruments={instrument}")
        return bool(got.get("instruments"))

    def place(self, sig, units: int) -> Fill:
        return self.market("XAU_USD", units, sig.stop, sig.targets[0])

    def market(self, instrument: str, units: int, stop: float,
               target: float, digits: int = 3) -> Fill:
        """A market order with its stop and target attached to the fill."""
        if units == 0:
            return Fill(False, "refused: zero units")
        body = {"order": {
            "type": "MARKET",
            "instrument": instrument,
            "units": str(units),
            "timeInForce": "FOK",
            "positionFill": "DEFAULT",
            # Attached on fill, so the position is never without a stop.
            "stopLossOnFill": {"price": f"{stop:.{digits}f}",
                               "timeInForce": "GTC"},
            "takeProfitOnFill": {"price": f"{target:.{digits}f}",
                                 "timeInForce": "GTC"},
        }}
        got = self._call("POST", f"/v3/accounts/{self.account}/orders", body)
        if "__error__" in got:
            return Fill(False, f"rejected: {json.dumps(got['__error__'])[:300]}")
        tx = got.get("orderFillTransaction")
        if tx:
            return Fill(True, "filled", tx.get("id"), float(tx.get("price", 0)) or None)
        cancel = got.get("orderCancelTransaction")
        if cancel:
            return Fill(False, f"cancelled: {cancel.get('reason')}")
        return Fill(False, f"unclear response: {json.dumps(got)[:300]}")


class PaperBroker:
    """Writes down the order and sends nothing.

    This is the default, and not out of timidity: the question of whether
    these signals make money is unanswered, and an unanswered question is a
    bad thing to put money behind. It records enough to answer it.
    """

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS orders (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        placed_at  INTEGER NOT NULL,
        instrument TEXT NOT NULL,
        units      INTEGER NOT NULL,
        entry      REAL,
        stop       REAL NOT NULL,
        target     REAL NOT NULL,
        reason     TEXT
    );
    """

    def __init__(self, db_path: str):
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.executescript(self.SCHEMA)
        self.practice = True

    def summary(self) -> dict:
        return {"account": {"balance": "paper", "currency": "USD"}}

    def tradeable(self, instrument: str = "XAU_USD") -> bool:
        return True

    def place(self, sig, units: int) -> Fill:
        return self.market("XAU_USD", units, sig.stop, sig.targets[0])

    def market(self, instrument: str, units: int, stop: float,
               target: float, digits: int = 3) -> Fill:
        import time
        self.db.execute(
            "INSERT INTO orders (placed_at, instrument, units, stop, target, reason)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (int(time.time()), instrument, units, stop, target, "paper"))
        self.db.commit()
        return Fill(True, "recorded on paper, nothing sent")
