"""Leader (TradingView alert) → guard rails → every following connection (PickMyTrade → Tradovate).

Run standalone:  uvicorn bridge.server:create_app --factory --host 0.0.0.0 --port 8000
The desktop app (desktop.py) runs the same thing in a window.

Two doors:
  * POST /webhook — public, for TradingView. Authenticated by the webhook secret inside the alert JSON.
  * /api/*        — the dashboard. Needs the session token (header X-Token), which only the app window knows.
"""
from __future__ import annotations

import asyncio
import contextlib
import re
import secrets
import time as _time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import BRAND, Account, Rules, Settings, load_accounts, load_settings, save_accounts
from .engine import NY, Signal, _hm, decide, render
from .news import News
from .store import Store

STATIC = Path(__file__).parent / "static"
RISK_REASONS = ("outside entry window", "max ", "daily loss", "profit target", "drawdown", "news blackout", "already in")
PROTECT_REASONS = ("kill switch", "account disabled")


def _iso_ago(minutes: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat(timespec="seconds")


class Bridge:
    def __init__(self, settings: Settings | None = None, accounts: list[Account] | None = None, sender=None, clock=None,
                 news: News | None = None, persist: bool = True):
        self.s = settings or load_settings()
        self.persist = persist and accounts is None
        self.accounts = accounts if accounts is not None else load_accounts(self.s.accounts_path)
        self.store = Store(self.s.db_path)
        self.sender = sender or self._post
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.news = news or News()
        self.lock = asyncio.Lock()
        self.seen: dict[str, float] = {}

    # ── connections ─────────────────────────────────────────────
    def save(self):
        if self.persist:
            save_accounts(self.s.accounts_path, self.accounts)

    def get(self, acc_id: str) -> Account:
        for a in self.accounts:
            if a.id == acc_id:
                return a
        raise HTTPException(404, "no such connection")

    @property
    def kill(self) -> bool:
        return bool(self.store.get("kill", False))

    # ── sending ────────────────────────────────────────────────
    async def _post(self, url: str, payload: dict) -> tuple[int, str]:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.post(url, json=payload)
            return r.status_code, r.text[:300]

    async def deliver(self, acc: Account, payload: dict, dry: bool = False) -> dict:
        if self.s.dry_run or dry:
            return dict(status="dry-run", ms=0)
        t0, err = _time.perf_counter(), ""
        for _ in range(2):
            try:
                code, body = await self.sender(acc.url, payload)
                return dict(status=code, body=body, ms=round((_time.perf_counter() - t0) * 1000))
            except Exception as e:                      # network error: one retry, then report
                err = repr(e)
                await asyncio.sleep(0.5)
        return dict(status="error", body=err, ms=round((_time.perf_counter() - t0) * 1000))

    # ── the leader signal ──────────────────────────────────────
    async def handle(self, raw: dict, dry: bool = False) -> list[dict]:
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
            self.store.log("duplicate", {k: v for k, v in raw.items() if k != "secret"})
            return []
        self.seen[key] = now_s

        now = self.clock()
        block = "" if sig.is_close else await self.news.blackout(now, self.s.news_blackout_min)
        async with self.lock:
            self.store.log("signal", {k: v for k, v in raw.items() if k != "secret"} | ({"test": True} if dry else {}))
            self.store.put("leader", dict(symbol=sig.symbol, position=sig.position, price=sig.price, at=now.isoformat()))
            out = []
            for acc in self.accounts:
                st = self.store.load_state(acc.id)
                d = decide(sig, acc, st, now, self.kill, block)
                rec = dict(reason=d.reason, qty=d.qty)
                if d.send:
                    rec |= await self.deliver(acc, d.payload, dry)
                    if not dry:
                        self.store.save_state(acc.id, st)
                        if d.trade:
                            self.store.log("trade", d.trade, acc.id)
                self.store.log("order" if d.send else "skip", rec | ({"test": True} if dry else {}), acc.id)
                out.append(dict(account=acc.id, send=d.send) | rec)
            return out

    async def flatten_all(self, why: str, only: str = "") -> list[dict]:
        """Close every connection the bridge believes is open — the end-of-day safety net and the panic button."""
        out = []
        async with self.lock:
            for acc in self.accounts:
                if only and acc.id != only:
                    continue
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

    async def cancel_all(self) -> list[dict]:
        out = []
        for acc in self.accounts:
            if not acc.template_cancel:
                out.append(dict(account=acc.id, status="no cancel template"))
                continue
            res = await self.deliver(acc, render(acc.template_cancel, dict(time=self.clock().isoformat())))
            self.store.log("cancel", res, acc.id)
            out.append(dict(account=acc.id) | res)
        return out

    # ── views ──────────────────────────────────────────────────
    def health(self) -> dict:
        since = _iso_ago(30)
        ev = self.store.events(2000, ("order", "skip", "flatten", "cancel"), since)
        fails = [e for e in ev if e["kind"] in ("order", "flatten", "cancel")
                 and (e["data"].get("status") == "error" or (isinstance(e["data"].get("status"), int) and e["data"]["status"] >= 400))]
        risk = [e for e in ev if e["kind"] == "skip" and any(r in e["data"].get("reason", "") for r in RISK_REASONS)]
        prot = [e for e in ev if e["kind"] == "skip" and any(r in e["data"].get("reason", "") for r in PROTECT_REASONS)]
        ms = [e["data"]["ms"] for e in ev if e["kind"] == "order" and isinstance(e["data"].get("status"), int) and e["data"].get("ms")]
        leader = self.store.get("leader") or {}
        want = {"long": 1, "short": -1, "flat": 0}.get(leader.get("position", "flat"), 0)
        out_sync = 0
        for a in self.accounts:
            if a.enabled and leader:
                pos = self.store.load_state(a.id).position
                out_sync += (pos > 0) - (pos < 0) != want
        status = "HEALTHY" if not fails and not out_sync else "ATTENTION"
        return dict(failures=len(fails), risk_blocks=len(risk), out_of_sync=out_sync, protected=len(prot),
                    avg_ms=round(sum(ms) / len(ms)) if ms else None, status=status)

    def rows(self) -> list[dict]:
        out = []
        for a in self.accounts:
            st = self.store.load_state(a.id)
            st.roll_day(self.clock().astimezone(NY).date().isoformat())
            out.append(dict(id=a.id, name=a.name or a.id, group=a.group, account=a.broker_account, follow=a.enabled,
                            symbol=st.symbol, side="LONG" if st.position > 0 else "SHORT" if st.position < 0 else "FLAT",
                            qty=abs(st.position), entry=st.entry_price, realized=round(st.realized_today, 2),
                            trades_today=st.trades_today, balance=round(st.balance, 2), micros_only=a.micros_only,
                            ratio=a.multiplier, room=round(st.room(a.rules.trailing_dd), 2), rules=a.rules.model_dump(),
                            target=a.rules.profit_target))
        return out

    def setup(self) -> dict:
        steps = [
            dict(key="connection", title="Add a connection", done=bool(self.accounts)),
            dict(key="template", title="Paste your PickMyTrade alert JSON",
                 done=any(a.template_open and "PASTE" not in str(a.template_open) for a in self.accounts)),
            dict(key="signal", title="Receive a first TradingView signal", done=bool(self.store.events(1, ("signal",)))),
            dict(key="live", title="Switch from test mode to live", done=not self.s.dry_run),
        ]
        return dict(steps=steps, done=sum(s["done"] for s in steps), total=len(steps))

    def state(self) -> dict:
        rows = self.rows()
        h = self.health()
        return dict(brand=BRAND, kill=self.kill, dry_run=self.s.dry_run, now=self.clock().isoformat(),
                    realized=round(sum(r["realized"] for r in rows), 2), open_positions=sum(r["qty"] > 0 for r in rows),
                    avg_ms=h["avg_ms"], rows=rows, health=h, setup=self.setup(),
                    events=self.store.events(60, ("signal", "order", "skip", "flatten", "cancel", "kill", "account")))

    def journal(self) -> dict:
        trades = [e["data"] | {"account": e["account"]} for e in self.store.events(2000, ("trade",))]
        pnl = [t["pnl"] for t in trades]
        wins = [p for p in pnl if p > 0]
        losses = [p for p in pnl if p <= 0]
        stats = dict(trades=len(pnl), win_rate=round(100 * len(wins) / len(pnl), 1) if pnl else 0, net=round(sum(pnl), 2),
                     avg_win=round(sum(wins) / len(wins), 2) if wins else 0,
                     avg_loss=round(-sum(losses) / len(losses), 2) if losses else 0)
        return dict(trades=trades, stats=stats)


# ── API models ─────────────────────────────────────────────────
class ConnectionIn(BaseModel):
    name: str
    group: str = ""
    broker_account: str = ""
    url: str = "https://api.pickmytrade.io/v2/add-trade-data"
    multiplier: float = 1.0
    micros_only: bool = False
    template_open: dict = {}
    template_close: dict = {}
    template_cancel: dict = {}
    rules: Rules = Rules()


class SettingsIn(BaseModel):
    dry_run: bool | None = None
    news_blackout_min: int | None = None
    public_url: str | None = None
    regenerate_secret: bool = False


def create_app(bridge: Bridge | None = None) -> FastAPI:
    b = bridge or Bridge()

    async def auto_flatten():
        """Safety net: at each connection's flatten time (NY) close it, once a day."""
        done: dict[str, str] = {}
        while True:
            now = b.clock().astimezone(NY)
            for a in list(b.accounts):
                if now.weekday() < 5 and now.time() >= _hm(a.rules.flatten_at) and done.get(a.id) != now.date().isoformat():
                    done[a.id] = now.date().isoformat()
                    await b.flatten_all(f"auto {a.rules.flatten_at} NY", only=a.id)
            await asyncio.sleep(20)

    @contextlib.asynccontextmanager
    async def lifespan(_app):
        task = asyncio.create_task(auto_flatten())
        yield
        task.cancel()

    app = FastAPI(title=BRAND, lifespan=lifespan)
    app.state.bridge = b
    app.mount("/static", StaticFiles(directory=STATIC), name="static")

    def token(x_token: str = Header(default="")):
        if not secrets.compare_digest(x_token, b.s.admin_token):
            raise HTTPException(401, "missing or wrong session token")

    auth = [Depends(token)]

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")

    @app.post("/webhook")
    async def webhook(req: Request):
        try:
            raw = await req.json()
        except Exception:
            raise HTTPException(400, "body must be JSON")
        if not isinstance(raw, dict):
            raise HTTPException(400, "body must be a JSON object")
        return {"results": await b.handle(raw)}

    @app.get("/api/state", dependencies=auth)
    def state():
        return b.state()

    @app.get("/api/journal", dependencies=auth)
    def journal():
        return b.journal()

    @app.get("/api/news", dependencies=auth)
    async def news():
        return await b.news.summary(b.clock())

    # connections
    @app.get("/api/connections", dependencies=auth)
    def connections():
        return [a.model_dump() for a in b.accounts]

    @app.post("/api/connections", dependencies=auth)
    def add_connection(c: ConnectionIn):
        base = re.sub(r"[^a-z0-9]+", "-", c.name.lower()).strip("-") or "conn"
        acc_id, n = base, 2
        while any(a.id == acc_id for a in b.accounts):
            acc_id, n = f"{base}-{n}", n + 1
        a = Account(id=acc_id, enabled=False, **c.model_dump())
        b.accounts.append(a)
        b.save()
        b.store.log("account", {"added": a.name}, a.id)
        return a.model_dump()

    @app.put("/api/connections/{acc_id}", dependencies=auth)
    def update_connection(acc_id: str, c: ConnectionIn):
        a = b.get(acc_id)
        for k, v in c.model_dump().items():
            setattr(a, k, Rules(**v) if k == "rules" else v)
        b.save()
        b.store.log("account", {"updated": a.name}, a.id)
        return a.model_dump()

    @app.delete("/api/connections/{acc_id}", dependencies=auth)
    def delete_connection(acc_id: str):
        a = b.get(acc_id)
        b.accounts.remove(a)
        b.save()
        b.store.log("account", {"removed": a.name}, acc_id)
        return {"ok": True}

    @app.post("/api/connections/{acc_id}/follow", dependencies=auth)
    def follow(acc_id: str, on: bool):
        a = b.get(acc_id)
        a.enabled = on
        b.save()
        b.store.log("account", {"follow": on}, acc_id)
        return {"id": acc_id, "follow": on}

    @app.post("/api/connections/{acc_id}/flatten", dependencies=auth)
    async def flatten_one(acc_id: str):
        b.get(acc_id)
        return {"results": await b.flatten_all("manual", only=acc_id)}

    @app.post("/api/followers", dependencies=auth)
    def all_followers(on: bool):
        for a in b.accounts:
            a.enabled = on
        b.save()
        b.store.log("account", {"follow_all": on})
        return {"follow": on}

    @app.post("/api/kill", dependencies=auth)
    def set_kill(on: bool):
        b.store.put("kill", on)
        b.store.log("kill", {"on": on})
        return {"kill": on}

    @app.post("/api/flatten", dependencies=auth)
    async def flatten():
        return {"results": await b.flatten_all("manual")}

    @app.post("/api/cancel", dependencies=auth)
    async def cancel():
        return {"results": await b.cancel_all()}

    @app.post("/api/test-signal", dependencies=auth)
    async def test_signal(action: str = "buy", position: str = "long"):
        """A fake leader signal that runs every rule but never sends anything."""
        raw = dict(secret=b.s.webhook_secret, strategy="test", symbol="MNQ1!", action=action, position=position,
                   contracts=1, price=0, id=f"test-{_time.time()}")
        return {"results": await b.handle(raw, dry=True)}

    # settings
    @app.get("/api/settings", dependencies=auth)
    def get_settings():
        return dict(brand=BRAND, dry_run=b.s.dry_run, news_blackout_min=b.s.news_blackout_min, public_url=b.s.public_url,
                    webhook_secret=b.s.webhook_secret, port=b.s.port, home=str(Path(b.s.home).resolve()))

    @app.put("/api/settings", dependencies=auth)
    def put_settings(s: SettingsIn):
        if s.dry_run is not None:
            b.s.dry_run = s.dry_run
        if s.news_blackout_min is not None:
            b.s.news_blackout_min = max(0, s.news_blackout_min)
        if s.public_url is not None:
            b.s.public_url = s.public_url.strip()
        if s.regenerate_secret:
            b.s.webhook_secret = secrets.token_urlsafe(18)
        if b.persist:
            b.s.save()
        b.store.log("settings", s.model_dump(exclude_none=True))
        return get_settings()

    @app.post("/api/feedback", dependencies=auth)
    async def feedback(req: Request):
        body = await req.json()
        b.store.log("feedback", {"text": str(body.get("text", ""))[:4000]})
        return {"ok": True}

    return app
