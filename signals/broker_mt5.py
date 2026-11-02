"""MetaTrader 5, through the terminal running on the same Windows machine.

The MetaTrader5 package does not talk to a broker; it talks to the terminal,
which must be open, logged in, and allowed to trade automatically (the "Algo
Trading" button). Whatever account the terminal is on is the account this
trades, which is why a real-money account is refused unless that is asked for
explicitly: the first connection should be to a demo, and a terminal left
logged into the wrong account is an easy mistake to make.

Orders go in as the signal describes them. A bare buy or sell is a market
order; a "Buy Stop" or "Sell Limit" is a pending order at his price, which
expires after a few hours if price never comes, as the paper settlement does.
The stop and target ride on the order itself, so a position is never briefly
without them.

Sizing arrives in units (ounces) and leaves in lots. A lot of gold is usually
a hundred ounces but the contract size is read from the symbol rather than
assumed, and the volume is rounded DOWN to the broker's step: a rounding
that adds size adds risk nobody chose.
"""
from __future__ import annotations

import json
import math
import os
import time
from dataclasses import dataclass

PENDING_HOURS = 4
MAGIC = 770077            # marks this bot's orders in the terminal's history
CANDIDATES = ("XAUUSD", "GOLD", "XAUUSD.", "XAUUSDm", "XAUUSD.a", "XAUUSD+")


@dataclass
class Fill:
    ok: bool
    detail: str
    order_id: str | None = None
    price: float | None = None


class Mt5Broker:
    def __init__(self, symbol: str | None = None, allow_real: bool = False,
                 track_path: str | None = None, start_balance: float | None = None,
                 be_at_r: float | None = 1.5, be_plus_usd: float = 1.0,
                 trail_step_usd: float | None = 1.0,
                 lock_ladder: list[tuple[float, float]] | None = None):
        try:
            import MetaTrader5 as mt5
        except ImportError:
            raise SystemExit("pip install MetaTrader5   (Windows, 64-bit Python)")
        self.mt5 = mt5
        if not mt5.initialize():
            raise SystemExit(f"cannot reach the MetaTrader 5 terminal: {mt5.last_error()}. "
                             "Is it open and logged in?")
        acc = mt5.account_info()
        if acc is None:
            raise SystemExit("the terminal is open but not logged into an account")
        self.demo = acc.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO
        if not self.demo and not allow_real:
            raise SystemExit(f"account {acc.login} on {acc.server} is a REAL account. "
                             "Set ALLOW_REAL=yes in .env only when that is intended.")
        info = mt5.terminal_info()
        if info is not None and not info.trade_allowed:
            raise SystemExit("Algo Trading is switched off in the terminal; "
                             "press the Algo Trading button so it turns green")
        self.practice = self.demo
        self.account = acc
        # The firm measures drawdown from where the account started, not from
        # wherever it happens to be today.
        self.start_balance = start_balance or acc.balance
        self.be_at_r = be_at_r
        self.be_plus = be_plus_usd
        self.trail_step = trail_step_usd
        # (share of the way to the target reached, share of the target locked)
        self.lock_ladder = sorted(lock_ladder or [])
        self.symbol = self._find_symbol(symbol)
        # Which desk trade each terminal ticket belongs to, kept on disk so a
        # restart does not forget positions that are still running.
        self.track_path = track_path
        self.tracked = {}
        if track_path and os.path.exists(track_path):
            try:
                self.tracked = json.load(open(track_path, encoding="utf-8"))
            except ValueError:
                self.tracked = {}

    # -- lookups -----------------------------------------------------------

    def _find_symbol(self, wanted: str | None) -> str:
        mt5 = self.mt5
        for name in ([wanted] if wanted else []) + list(CANDIDATES):
            info = mt5.symbol_info(name)
            if info is None:
                continue
            if not info.visible:
                mt5.symbol_select(name, True)
            return name
        raise SystemExit("no gold symbol found on this account; set MT5_SYMBOL in .env "
                         f"to the name the terminal uses (tried {', '.join(CANDIDATES)})")

    def summary(self) -> dict:
        acc = self.mt5.account_info()
        return {"account": {"balance": str(acc.balance), "currency": acc.currency}}

    def tradeable(self, instrument: str = "XAU_USD") -> bool:
        info = self.mt5.symbol_info(self.symbol)
        return info is not None and info.trade_mode != self.mt5.SYMBOL_TRADE_MODE_DISABLED

    def describe(self) -> str:
        a = self.account
        kind = "DEMO" if self.demo else "REAL MONEY"
        return f"MT5 {kind} {a.login} on {a.server}, {self.symbol}, balance {a.balance} {a.currency}"

    # -- orders ------------------------------------------------------------

    def _lots(self, units: int) -> tuple[float, str | None]:
        info = self.mt5.symbol_info(self.symbol)
        size = info.trade_contract_size or 100.0
        step = info.volume_step or 0.01
        raw = abs(units) / size
        lots = math.floor(raw / step + 1e-9) * step
        lots = round(min(lots, info.volume_max), 8)
        if lots < info.volume_min:
            return 0.0, (f"{abs(units)} oz is {raw:.4f} lots, under this broker's minimum "
                         f"of {info.volume_min}; not rounded up, since that would add risk")
        return lots, None

    def _filling(self, pending: bool) -> int:
        mt5 = self.mt5
        if pending:
            return mt5.ORDER_FILLING_RETURN
        mode = self.mt5.symbol_info(self.symbol).filling_mode
        if mode & 1:
            return mt5.ORDER_FILLING_FOK
        if mode & 2:
            return mt5.ORDER_FILLING_IOC
        return mt5.ORDER_FILLING_RETURN

    def place(self, sig, units: int) -> Fill:
        mt5 = self.mt5
        lots, why = self._lots(units)
        if why:
            return Fill(False, f"refused: {why}")
        buy = sig.side == "buy"
        order = getattr(sig, "order", None) or "market"
        digits = mt5.symbol_info(self.symbol).digits
        req = {
            "symbol": self.symbol,
            "volume": lots,
            "sl": round(sig.stop, digits),
            "tp": round(sig.targets[0], digits),
            "deviation": 30,
            "magic": MAGIC,
            "comment": "tape",
        }
        if order == "market":
            tick = mt5.symbol_info_tick(self.symbol)
            req.update(action=mt5.TRADE_ACTION_DEAL,
                       type=mt5.ORDER_TYPE_BUY if buy else mt5.ORDER_TYPE_SELL,
                       price=tick.ask if buy else tick.bid,
                       type_time=mt5.ORDER_TIME_GTC,
                       type_filling=self._filling(False))
        else:
            kinds = {("buy", "stop"): mt5.ORDER_TYPE_BUY_STOP,
                     ("sell", "stop"): mt5.ORDER_TYPE_SELL_STOP,
                     ("buy", "limit"): mt5.ORDER_TYPE_BUY_LIMIT,
                     ("sell", "limit"): mt5.ORDER_TYPE_SELL_LIMIT}
            req.update(action=mt5.TRADE_ACTION_PENDING,
                       type=kinds[(sig.side, order)],
                       price=round(sig.entry, digits),
                       type_time=mt5.ORDER_TIME_SPECIFIED,
                       expiration=int(time.time() + PENDING_HOURS * 3600),
                       type_filling=self._filling(True))

        res = mt5.order_send(req)
        if res is None:
            return Fill(False, f"terminal refused the request: {mt5.last_error()}")
        if res.retcode == mt5.TRADE_RETCODE_INVALID_EXPIRATION and order != "market":
            # Some brokers only take good-till-cancelled pending orders.
            req.update(type_time=mt5.ORDER_TIME_GTC)
            req.pop("expiration", None)
            res = mt5.order_send(req)
        ok_codes = (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED)
        if res.retcode not in ok_codes:
            return Fill(False, f"rejected {res.retcode}: {res.comment}")
        what = "filled" if order == "market" else f"{order} order placed"
        return Fill(True, f"{what}, {lots} lots on {self.symbol}",
                    str(res.order), res.price or (sig.entry if order != "market" else None))

    def close_all(self) -> list[str]:
        """Closes every open position on the bot's symbol and cancels every
        pending order the bot placed. The emergency button on the desk ends
        here. Returns one line per action, failures included, so the owner
        sees exactly what is still open."""
        mt5 = self.mt5
        done = []
        for o in mt5.orders_get(symbol=self.symbol) or []:
            if o.magic != MAGIC:
                continue
            res = mt5.order_send({"action": mt5.TRADE_ACTION_REMOVE, "order": o.ticket})
            ok = res is not None and res.retcode == mt5.TRADE_RETCODE_DONE
            done.append(f"{'cancelled' if ok else 'FAILED to cancel'} pending order {o.ticket}")
        for p in mt5.positions_get(symbol=self.symbol) or []:
            buy = p.type == mt5.POSITION_TYPE_BUY
            tick = mt5.symbol_info_tick(self.symbol)
            res = mt5.order_send({
                "action": mt5.TRADE_ACTION_DEAL, "symbol": self.symbol, "position": p.ticket,
                "volume": p.volume, "type": mt5.ORDER_TYPE_SELL if buy else mt5.ORDER_TYPE_BUY,
                "price": tick.bid if buy else tick.ask, "deviation": 50, "magic": MAGIC,
                "comment": "tape close all", "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": self._filling(False)})
            ok = res is not None and res.retcode in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED)
            done.append(f"{'closed' if ok else 'FAILED to close'} position {p.ticket} "
                        f"({p.volume} lots)" + ("" if ok else f": {getattr(res, 'comment', mt5.last_error())}"))
        return done or ["nothing was open"]

    # -- following positions to their end ---------------------------------

    def track(self, trade_id: int, order_id: str, pending: bool,
              side: str | None = None, stop: float | None = None, msg: int | None = None,
              tp: float | None = None) -> None:
        self.tracked[str(order_id)] = {"trade": trade_id, "pending": pending,
                                       "side": side, "stop": stop, "tp": tp, "be": False,
                                       "msg": msg, "at": time.time()}
        self._save()

    def holds_same(self, side: str, stop: float, tp: float, tol: float = 0.6) -> bool:
        """Whether an order or position the bot still holds has this side,
        stop and target, within cents: the same trade posted twice."""
        mt5 = self.mt5
        for tk, t in self.tracked.items():
            if t.get("side") != side or t.get("stop") is None or t.get("tp") is None:
                continue
            if abs(t["stop"] - stop) > tol or abs(t["tp"] - tp) > tol:
                continue
            if mt5.positions_get(ticket=int(tk)) or mt5.orders_get(ticket=int(tk)):
                return True
        return False

    def cancel_signal(self, msg: int | None) -> list[str]:
        """The channel's "CLOSE ORDER": takes back what one signal opened.

        The order is found by the signal message it answers; with no reply to
        go by, the newest order from the last six hours. A pending order is
        cancelled; one that has already filled is closed at the market, since
        the signal it came from has been called off. Following then reports
        the cancel or the close to the desk, as for any other ending."""
        mt5 = self.mt5
        mine = [(tk, t) for tk, t in self.tracked.items() if msg is not None and t.get("msg") == msg]
        if not mine and self.tracked:
            recent = [(tk, t) for tk, t in self.tracked.items() if time.time() - t.get("at", 0) < 6 * 3600]
            mine = recent[-1:]
        if not mine:
            return ["no order of the bot's matches it"]
        done = []
        for tk, t in mine:
            ticket = int(tk)
            pos = mt5.positions_get(ticket=ticket)
            if pos:
                p = pos[0]
                buy = p.type == mt5.POSITION_TYPE_BUY
                tick = mt5.symbol_info_tick(self.symbol)
                res = mt5.order_send({
                    "action": mt5.TRADE_ACTION_DEAL, "symbol": self.symbol, "position": ticket,
                    "volume": p.volume, "type": mt5.ORDER_TYPE_SELL if buy else mt5.ORDER_TYPE_BUY,
                    "price": tick.bid if buy else tick.ask, "deviation": 50, "magic": MAGIC,
                    "comment": "tape close order", "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": self._filling(False)})
                ok = res is not None and res.retcode in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED)
                done.append(f"{'closed' if ok else 'FAILED to close'} the filled trade {ticket}")
            elif mt5.orders_get(ticket=ticket):
                res = mt5.order_send({"action": mt5.TRADE_ACTION_REMOVE, "order": ticket})
                ok = res is not None and res.retcode == mt5.TRADE_RETCODE_DONE
                done.append(f"{'cancelled' if ok else 'FAILED to cancel'} the pending order {ticket}")
            else:
                done.append(f"order {ticket} had already ended")
        return done

    # -- the account, as the guard needs to see it --------------------------

    def state(self):
        """Losses today and overall, open risk and position count.

        Floating losses count, because a funded account counts them. Pending
        orders count as open risk, because any of them may fill.
        """
        from risk import AccountState
        mt5 = self.mt5
        acc = mt5.account_info()
        info = mt5.symbol_info(self.symbol)
        size = info.trade_contract_size or 100.0
        now = mt5.symbol_info_tick(self.symbol).time      # broker's clock
        day_start = now - now % 86400
        deals = mt5.history_deals_get(day_start, now + 60) or []
        realized = sum(d.profit + d.commission + d.swap for d in deals
                       if d.type != getattr(mt5, "DEAL_TYPE_BALANCE", 2))
        positions = mt5.positions_get() or []
        floating = sum(p.profit + p.swap for p in positions)

        def at_risk(open_price, sl, volume, buy):
            if not sl:
                return open_price * volume * size        # no stop: everything
            loss = (open_price - sl) if buy else (sl - open_price)
            return max(0.0, loss) * volume * size

        risk = sum(at_risk(p.price_open, p.sl, p.volume, p.type == mt5.POSITION_TYPE_BUY)
                   for p in positions)
        orders = mt5.orders_get() or []
        risk += sum(at_risk(o.price_open, o.sl, o.volume_current,
                            o.type in (mt5.ORDER_TYPE_BUY_STOP, mt5.ORDER_TYPE_BUY_LIMIT))
                    for o in orders)
        # Every order this bot placed today, whether it filled, is pending,
        # closed or expired. Stop and target closes are the broker's orders,
        # not the bot's, so only orders it sent itself are counted.
        placed = {o.ticket for o in (mt5.history_orders_get(day_start, now + 60) or [])
                  if o.magic == MAGIC and o.time_setup >= day_start
                  and o.reason == getattr(mt5, "ORDER_REASON_EXPERT", 3)}
        placed |= {o.ticket for o in orders if o.magic == MAGIC and o.time_setup >= day_start}
        return AccountState(
            balance=acc.balance,
            equity=acc.equity,
            day_loss=max(0.0, -(realized + floating)),
            total_loss=max(0.0, self.start_balance - acc.equity),
            open_risk=risk,
            open_count=len(positions) + len(orders),
            trades_today=len(placed),
        )

    def _break_even(self) -> list[dict]:
        """Moves a stop to entry plus a dollar once price has gone far enough.

        Plus a dollar, not to the entry itself: a stop at the entry closes
        the trade at a small loss once spread and commission are paid.
        """
        if not self.be_at_r and not self.trail_step and not self.lock_ladder:
            return []
        mt5 = self.mt5
        events = []
        for ticket, t in self.tracked.items():
            if t.get("pending") or t.get("stop") is None:
                continue
            pos = mt5.positions_get(ticket=int(ticket))
            if not pos:
                continue
            p = pos[0]
            buy = p.type == mt5.POSITION_TYPE_BUY
            risk = abs(p.price_open - t["stop"])
            tick = mt5.symbol_info_tick(p.symbol)
            gained = (tick.bid - p.price_open) if buy else (p.price_open - tick.ask)
            digits = mt5.symbol_info(p.symbol).digits
            cur_sl = p.sl
            # The owner's rule: every $1 (10 pips) in profit pulls the stop $1
            # closer, until it sits on the entry, and goes no further.
            if self.trail_step and risk > 0 and gained >= self.trail_step:
                steps = int(gained // self.trail_step)
                want = (min(t["stop"] + steps * self.trail_step, p.price_open) if buy
                        else max(t["stop"] - steps * self.trail_step, p.price_open))
                want = round(want, digits)
                better = (buy and (not cur_sl or want > cur_sl + 1e-9)) or (not buy and (not cur_sl or want < cur_sl - 1e-9))
                if better:
                    res = mt5.order_send({"action": mt5.TRADE_ACTION_SLTP, "position": p.ticket,
                                          "symbol": p.symbol, "sl": want, "tp": p.tp})
                    if res is not None and res.retcode == mt5.TRADE_RETCODE_DONE:
                        cur_sl = want
                        events.append({"type": "trail", "trade_id": t["trade"], "sl": want,
                                       "at_entry": abs(want - p.price_open) < 1e-6,
                                       "ts": int(time.time())})
            # Past the entry: lock a share of the target as price nears it, so
            # a trade that turns back short of the target still pays something.
            tp = p.tp or t.get("tp")
            dist = abs(tp - p.price_open) if tp else 0
            if self.lock_ladder and dist > 0 and gained > 0:
                reached = [lock for at, lock in self.lock_ladder if gained >= at * dist]
                if reached:
                    lock = reached[-1]
                    want = round(p.price_open + lock * dist if buy else p.price_open - lock * dist, digits)
                    better = (buy and (not cur_sl or want > cur_sl + 1e-9)) or (not buy and (not cur_sl or want < cur_sl - 1e-9))
                    if better:
                        res = mt5.order_send({"action": mt5.TRADE_ACTION_SLTP, "position": p.ticket,
                                              "symbol": p.symbol, "sl": want, "tp": p.tp})
                        if res is not None and res.retcode == mt5.TRADE_RETCODE_DONE:
                            cur_sl = want
                            events.append({"type": "lock", "trade_id": t["trade"], "sl": want,
                                           "locked_pct": round(lock * 100),
                                           "ts": int(time.time())})
            if t.get("be") or not self.be_at_r or risk <= 0 or gained < self.be_at_r * risk:
                continue
            new_sl = round(p.price_open + self.be_plus if buy else p.price_open - self.be_plus, digits)
            if (buy and cur_sl and cur_sl >= new_sl) or (not buy and cur_sl and cur_sl <= new_sl):
                t["be"] = True                        # already at least this safe
                continue
            res = mt5.order_send({"action": mt5.TRADE_ACTION_SLTP, "position": p.ticket,
                                  "symbol": p.symbol, "sl": new_sl, "tp": p.tp})
            if res is not None and res.retcode == mt5.TRADE_RETCODE_DONE:
                t["be"] = True
                events.append({"type": "be", "trade_id": t["trade"], "sl": new_sl,
                               "ts": int(time.time())})
        return events

    def _save(self) -> None:
        if self.track_path:
            json.dump(self.tracked, open(self.track_path, "w", encoding="utf-8"))

    def poll(self) -> list[dict]:
        """What happened to tracked tickets since last asked.

        Returns desk events: a pending order filling, expiring or being
        cancelled, and a position closing at its stop, its target or by hand.
        """
        mt5 = self.mt5
        events = self._break_even()
        for ticket, t in list(self.tracked.items()):
            tk = int(ticket)
            if t["pending"]:
                live = mt5.orders_get(ticket=tk)
                if live:
                    continue                      # still waiting
                hist = mt5.history_orders_get(ticket=tk)
                state = hist[0].state if hist else None
                if state == mt5.ORDER_STATE_FILLED:
                    deals = mt5.history_deals_get(position=tk) or []
                    entry = next((d for d in deals if d.entry == mt5.DEAL_ENTRY_IN), None)
                    events.append({"type": "fill", "trade_id": t["trade"],
                                   "entry": entry.price if entry else None,
                                   "ts": int(entry.time) if entry else int(time.time())})
                    t["pending"] = False
                elif state is not None:
                    events.append({"type": "expire", "trade_id": t["trade"],
                                   "ts": int(time.time())})
                    self.tracked.pop(ticket)
                continue

            if mt5.positions_get(ticket=tk):
                continue                          # still open
            # By position only: given dates as well, the terminal ignores the
            # position and returns every deal in the range, the deposit
            # included, which once reported a whole balance as one trade's profit.
            deals = [d for d in (mt5.history_deals_get(position=tk) or [])
                     if d.position_id == tk and d.type != getattr(mt5, "DEAL_TYPE_BALANCE", 2)]
            out = [d for d in deals if d.entry == mt5.DEAL_ENTRY_OUT]
            if not out:
                continue
            last = out[-1]
            outcome = {mt5.DEAL_REASON_TP: "tp", mt5.DEAL_REASON_SL: "sl"}.get(last.reason, "manual")
            events.append({"type": "close", "trade_id": t["trade"], "exit": last.price,
                           "outcome": outcome, "ts": int(last.time),
                           "profit": sum(d.profit + d.commission + d.swap for d in deals)})
            self.tracked.pop(ticket)
        self._save()
        return events
