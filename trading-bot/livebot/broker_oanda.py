"""Minimal OANDA v20 REST client (practice or live). Docs: https://developer.oanda.com/rest-live-v20/introduction/"""
from __future__ import annotations

import math
from datetime import datetime, timezone

import requests

from strategy import Candle

HOSTS = {"practice": "https://api-fxpractice.oanda.com", "live": "https://api-fxtrade.oanda.com"}


class Oanda:
    def __init__(self, token: str, account_id: str, environment: str = "practice", instrument: str = "NAS100_USD"):
        self.base = HOSTS[environment]
        self.account = account_id
        self.instrument = instrument
        self.s = requests.Session()
        self.s.headers.update({"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                               "Accept-Datetime-Format": "RFC3339"})
        self._spec = None

    def _get(self, path: str, **params):
        r = self.s.get(self.base + path, params=params, timeout=20)
        r.raise_for_status()
        return r.json()

    def _send(self, method: str, path: str, body: dict):
        r = self.s.request(method, self.base + path, json=body, timeout=20)
        if r.status_code >= 400:
            raise RuntimeError(f"OANDA {method} {path} → {r.status_code}: {r.text}")
        return r.json()

    # ---- account / instrument ----
    def balance(self) -> float:
        return float(self._get(f"/v3/accounts/{self.account}/summary")["account"]["balance"])

    def spec(self) -> dict:
        if self._spec is None:
            j = self._get(f"/v3/accounts/{self.account}/instruments", instruments=self.instrument)
            self._spec = j["instruments"][0]
        return self._spec

    def price_str(self, x: float) -> str:
        return f"{x:.{int(self.spec()['displayPrecision'])}f}"

    def units_for_risk(self, risk_usd: float, stop_points: float) -> float:
        """NAS100_USD: 1 unit = 1 USD per index point."""
        prec = int(self.spec()["tradeUnitsPrecision"])
        units = math.floor(risk_usd / stop_points * 10 ** prec) / 10 ** prec
        return units if units >= float(self.spec()["minimumTradeSize"]) else 0.0

    # ---- data ----
    def candles_m1(self, count: int = 5000) -> list[Candle]:
        return self.candles("M1", count)

    def candles(self, granularity: str, count: int = 5000) -> list[Candle]:
        j = self._get(f"/v3/instruments/{self.instrument}/candles", granularity=granularity, count=count, price="M")
        out = []
        for k in j["candles"]:
            if not k["complete"]:
                continue
            m = k["mid"]
            t = datetime.fromisoformat(k["time"][:19]).replace(tzinfo=timezone.utc)      # RFC3339 with nanoseconds, UTC
            out.append(Candle(t, float(m["o"]), float(m["h"]), float(m["l"]), float(m["c"])))
        return out

    # ---- orders ----
    def place_stop_entry(self, side: int, units: float, level: float, stop_distance: float, trail_distance: float,
                         good_till: datetime) -> dict:
        prec = int(self.spec()["tradeUnitsPrecision"])
        order = {
            "type": "STOP", "instrument": self.instrument,
            "units": f"{side * units:.{prec}f}", "price": self.price_str(level),
            "timeInForce": "GTD", "gtdTime": good_till.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000000000Z"),
            "positionFill": "DEFAULT", "triggerCondition": "DEFAULT",
            "stopLossOnFill": {"distance": self.price_str(stop_distance), "timeInForce": "GTC"},
            "trailingStopLossOnFill": {"distance": self.price_str(trail_distance), "timeInForce": "GTC"},
            "clientExtensions": {"tag": "gapfb", "comment": "GapFB-NQ"},
            "tradeClientExtensions": {"tag": "gapfb"},
        }
        return self._send("POST", f"/v3/accounts/{self.account}/orders", {"order": order})

    def market_bracket(self, tag: str, side: int, units: float, stop_distance: float, target_distance: float) -> dict:
        prec = int(self.spec()["tradeUnitsPrecision"])
        order = {"type": "MARKET", "instrument": self.instrument, "units": f"{side * units:.{prec}f}", "timeInForce": "FOK",
                 "positionFill": "DEFAULT",
                 "stopLossOnFill": {"distance": self.price_str(stop_distance), "timeInForce": "GTC"},
                 "takeProfitOnFill": {"distance": self.price_str(target_distance), "timeInForce": "GTC"},
                 "tradeClientExtensions": {"tag": tag}}
        return self._send("POST", f"/v3/accounts/{self.account}/orders", {"order": order})

    def open_trades(self) -> list[dict]:
        return [t for t in self._get(f"/v3/accounts/{self.account}/openTrades")["trades"] if t["instrument"] == self.instrument]

    def close_tagged(self, tag: str) -> int:
        n = 0
        for t in self.open_trades():
            if t.get("clientExtensions", {}).get("tag") == tag:
                self._send("PUT", f"/v3/accounts/{self.account}/trades/{t['id']}/close", {"units": "ALL"}); n += 1
        return n

    def net_side(self) -> int:
        u = sum(float(t["currentUnits"]) for t in self.open_trades())
        return 0 if u == 0 else (1 if u > 0 else -1)

    def cancel_pending(self) -> int:
        n = 0
        for o in self._get(f"/v3/accounts/{self.account}/pendingOrders").get("orders", []):
            if o.get("instrument") == self.instrument and o.get("type") == "STOP":
                self._send("PUT", f"/v3/accounts/{self.account}/orders/{o['id']}/cancel", {})
                n += 1
        return n

    def close_position(self) -> dict | None:
        pos = self._get(f"/v3/accounts/{self.account}/positions/{self.instrument}")["position"]
        body = {}
        if float(pos["long"]["units"]) != 0:
            body["longUnits"] = "ALL"
        if float(pos["short"]["units"]) != 0:
            body["shortUnits"] = "ALL"
        if not body:
            return None
        return self._send("PUT", f"/v3/accounts/{self.account}/positions/{self.instrument}/close", body)

    def closed_trades(self, count: int = 20) -> list[dict]:
        return self._get(f"/v3/accounts/{self.account}/trades", state="CLOSED", instrument=self.instrument, count=count)["trades"]
