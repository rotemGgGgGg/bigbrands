"""TradingView → bridge → PickMyTrade (one request per enabled account) → Tradovate.

Run:  uvicorn bridge.server:create_app --factory --host 0.0.0.0 --port 8000
Env:  BRIDGE_SECRET (required), BRIDGE_ADMIN_PASS (required for the dashboard), BRIDGE_DRY_RUN=0 to really send.
"""
from __future__ import annotations

import asyncio
import contextlib
import secrets
import time as _time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from .config import Account, load_accounts, load_settings
from .engine import NY, Signal, _hm, decide, render
from .store import Store

STATIC = Path(__file__).parent / "static"


class Bridge:
    def __init__(self, settings=None, accounts: list[Account] | None = None, sender=None, clock=None):
        self.s = settings or load_settings()
        self.accounts = accounts if accounts is not None else load_accounts(self.s.accounts_path)
        self.store = Store(self.s.db_path)
        self.sender = sender or self._post
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.lock = asyncio.Lock()
        self.seen: dict[str, float] = {}
        for a in self.accounts:                          # dashboard on/off survives a restart
            on = self.store.get(f"enabled:{a.id}")
            if on is not None:
                a.enabled = on

    @property
    def kill(self) -> bool:
        return bool(self.store.get("kill", False))

    async def _post(self, url: str, payload: dict) -> tuple[int, str]:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.post(url, json=payload)
            return r.status_code, r.text[:300]

    async def deliver(self, acc: Account, payload: dict) -> dict:
        if self.s.dry_run:
            return dict(status="dry-run")
        for attempt in range(2):
            try:
                code, body = await self.sender(acc.url, payload)
                return dict(status=code, body=body)
            except Exception as e:                      # network error: one retry, then report
                err = repr(e)
                await asyncio.sleep(0.5)
        return dict(status="error", body=err)

    async def handle(self, raw: dict) -> list[dict]:
        if not self.s.webhook_secret or not secrets.compare_digest(str(raw.get("secret", "")), self.s.webhook_secret):
            raise HTTPException(401, "bad secret")
        try:
            sig = Signal(strategy=str(raw.get("strategy", "")), symbol=str(raw["symbol"]), action=str(raw["action"]).lower(),
                         contracts=float(raw.get("contracts", 1) or 1), position=str(raw["position"]).lower(),
                         price=float(raw["price"]), order_id=str(raw.get("id", "")),
                         sl=float(raw.get("sl", 0) or 0), tp=float(raw.get("tp", 0) or 0))
        except (KeyError, ValueError) as e:
            raise HTTPException(422, f"bad alert: {e}")
        if sig.action not in ("buy", "sell") or sig.position not in ("long", "short", "flat"):
            raise HTTPException(422, "action must be buy/sell, position long/short/flat")

        key = f"{sig.strategy}|{sig.order_id}|{sig.action}|{sig.position}|{sig.price}"
        now_s = _time.time()
        self.seen = {k: v for k, v in self.seen.items() if now_s - v < 60}
        if key in self.seen:                            # TradingView can fire the same alert twice
            self.store.log("duplicate", raw | {"secret": "***"})
            return []
        self.seen[key] = now_s

        async with self.lock:
            self.store.log("signal", {k: v for k, v in raw.items() if k != "secret"})
            out = []
            for acc in self.accounts:
                st = self.store.load_state(acc.id)
                d = decide(sig, acc, st, self.clock(), self.kill)
                rec = dict(reason=d.reason, qty=d.qty)
                if d.send:
                    rec |= await self.deliver(acc, d.payload)
                    self.store.save_state(acc.id, st)
                self.store.log("order" if d.send else "skip", rec, acc.id)
                out.append(dict(account=acc.id, send=d.send) | rec)
            return out

    async def flatten_all(self, why: str) -> list[dict]:
        """Close every account the bridge believes is open — the end-of-day safety net and the panic button."""
        out = []
        async with self.lock:
            for acc in self.accounts:
                st = self.store.load_state(acc.id)
                if st.position == 0:
                    continue
                side = "sell" if st.position > 0 else "buy"
                payload = render(acc.template_close, dict(side=side, qty=abs(st.position), symbol=st.symbol, price=0,
                                                                time=self.clock().isoformat()))
                res = await self.deliver(acc, payload)
                st.position, st.entry_price = 0, 0.0     # P&L unknown without a price — the broker has the truth
                self.store.save_state(acc.id, st)
                self.store.log("flatten", dict(reason=why) | res, acc.id)
                out.append(dict(account=acc.id) | res)
        return out

    def snapshot(self) -> dict:
        accs = []
        for a in self.accounts:
            st = self.store.load_state(a.id)
            accs.append(dict(id=a.id, name=a.name or a.id, enabled=a.enabled, multiplier=a.multiplier,
                             position=st.position, symbol=st.symbol, entry=st.entry_price, today=round(st.realized_today, 2),
                             trades_today=st.trades_today, balance=round(st.balance, 2),
                             room=round(st.room(a.rules.trailing_dd), 2), target=a.rules.profit_target))
        return dict(kill=self.kill, dry_run=self.s.dry_run, accounts=accs, events=self.store.events(80),
                    now_ny=self.clock().astimezone(NY).strftime("%Y-%m-%d %H:%M:%S"))


def create_app(bridge: Bridge | None = None) -> FastAPI:
    b = bridge or Bridge()

    async def auto_flatten():
        """Safety net: at the flatten time (NY) close whatever the bridge believes is open, once a day."""
        done = ""
        while True:
            now = b.clock().astimezone(NY)
            at = b.accounts[0].rules.flatten_at if b.accounts else "15:55"
            if now.time() >= _hm(at) and done != now.date().isoformat():
                done = now.date().isoformat()
                await b.flatten_all(f"auto {at} NY")
            await asyncio.sleep(20)

    @contextlib.asynccontextmanager
    async def lifespan(_app):
        task = asyncio.create_task(auto_flatten())
        yield
        task.cancel()

    app = FastAPI(title="Trading bridge", lifespan=lifespan)
    app.state.bridge = b
    basic = HTTPBasic()

    def admin(c: HTTPBasicCredentials = Depends(basic)):
        ok = b.s.admin_pass and secrets.compare_digest(c.username, b.s.admin_user) and secrets.compare_digest(c.password, b.s.admin_pass)
        if not ok:
            raise HTTPException(401, "unauthorized", headers={"WWW-Authenticate": "Basic"})

    @app.post("/webhook")
    async def webhook(req: Request):
        try:
            raw = await req.json()
        except Exception:
            raise HTTPException(400, "body must be JSON")
        return {"results": await b.handle(raw)}

    @app.get("/", dependencies=[Depends(admin)])
    def dashboard():
        return FileResponse(STATIC / "index.html")

    @app.get("/api/state", dependencies=[Depends(admin)])
    def state():
        return b.snapshot()

    @app.post("/api/kill", dependencies=[Depends(admin)])
    def set_kill(on: bool):
        b.store.put("kill", on)
        b.store.log("kill", {"on": on})
        return {"kill": on}

    @app.post("/api/accounts/{acc_id}/enabled", dependencies=[Depends(admin)])
    def set_enabled(acc_id: str, on: bool):
        for a in b.accounts:
            if a.id == acc_id:
                a.enabled = on
                b.store.put(f"enabled:{acc_id}", on)
                b.store.log("account", {"enabled": on}, acc_id)
                return {"id": acc_id, "enabled": on}
        raise HTTPException(404, "no such account")

    @app.post("/api/flatten", dependencies=[Depends(admin)])
    async def flatten():
        return {"results": await b.flatten_all("manual")}

    return app

