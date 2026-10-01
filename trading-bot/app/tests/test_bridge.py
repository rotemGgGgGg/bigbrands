"""Bridge tests: guard rails, copy trading, templates, the webhook and the dashboard API. No network."""
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bridge.config import Account, Rules, Settings, point_value, to_micro  # noqa: E402
from bridge.engine import AccountState, Signal, decide, render  # noqa: E402
from bridge.news import News  # noqa: E402
from bridge.server import Bridge, create_app  # noqa: E402

NY = ZoneInfo("America/New_York")
OPEN_T = {"symbol": "{{symbol}}", "data": "{{side}}", "quantity": "{{qty}}", "sl": "{{sl}}", "tp": "{{tp}}", "token": "T"}
CLOSE_T = {"symbol": "{{symbol}}", "data": "close", "quantity": "{{qty}}", "token": "T"}


def at(h, m, d=15):
    return datetime(2026, 10, d, h, m, tzinfo=NY)


def acc(**kw):
    return Account(id=kw.pop("id", "a1"), enabled=True, template_open=OPEN_T, template_close=CLOSE_T, **kw)


def sig(action="buy", position="long", price=20000.0, contracts=1, sl=0.0):
    return Signal("t", "MNQ1!", action, contracts, position, price, sl=sl)


def test_point_value():
    assert point_value("MNQ1!") == 2.0
    assert point_value("CME_MINI:NQZ2026") == 20.0
    assert point_value("MES1!") == 5.0


def test_to_micro():
    assert to_micro("NQ1!") == "MNQ1!" and to_micro("CME_MINI:ESZ2026") == "MESZ2026" and to_micro("MNQ1!") == "MNQ1!"


def test_micros_only_sends_micro_symbol():
    a = acc(micros_only=True)
    d = decide(Signal("t", "NQ1!", "buy", 1, "long", 20000.0), a, AccountState(), at(10, 0), False)
    assert d.payload["symbol"] == "MNQ1!"


def test_news_block_stops_entries():
    d = decide(sig(), acc(), AccountState(), at(10, 0), False, block="news blackout: NFP")
    assert not d.send and "news" in d.reason


def test_render_keeps_types():
    out = render(OPEN_T, dict(symbol="MNQ1!", side="buy", qty=2, sl=10.0, tp=20.0))
    assert out == {"symbol": "MNQ1!", "data": "buy", "quantity": 2, "sl": 10.0, "tp": 20.0, "token": "T"}


def test_open_then_close_tracks_pnl():
    a, st = acc(), AccountState()
    d = decide(sig(), a, st, at(10, 0), kill=False)
    assert d.send and d.qty == 1 and st.position == 1
    d = decide(sig("sell", "flat", price=20025.0), a, st, at(10, 30), kill=False)
    assert d.send and d.payload["data"] == "close" and st.position == 0
    assert st.realized_today == 50.0 and st.balance == 50.0       # 25 points × $2


def test_entry_window_and_kill_switch_block_entries_not_exits():
    a, st = acc(), AccountState()
    assert not decide(sig(), a, st, at(8, 0), kill=False).send
    assert decide(sig(), a, st, at(10, 0), kill=False).send
    assert not decide(sig(), a, AccountState(), at(10, 0), kill=True).send
    d = decide(sig("sell", "flat"), a, st, at(10, 5), kill=True)   # the exit still goes out
    assert d.send


def test_daily_loss_limit_and_max_trades():
    a = acc(rules=Rules(daily_loss_limit=100, max_trades_per_day=5))
    st = AccountState()
    decide(sig(price=20000), a, st, at(10, 0), False)
    decide(sig("sell", "flat", price=19940), a, st, at(10, 5), False)    # −$120
    assert st.realized_today == -120
    d = decide(sig(), a, st, at(10, 10), False)
    assert not d.send and "daily loss" in d.reason
    st2 = AccountState()
    a2 = acc(rules=Rules(max_trades_per_day=1))
    decide(sig(), a2, st2, at(10, 0), False)
    decide(sig("sell", "flat"), a2, st2, at(10, 5), False)
    assert "max 1 trades" in decide(sig(), a2, st2, at(10, 10), False).reason


def test_trailing_drawdown_guard():
    a = acc(rules=Rules(trailing_dd=2000, dd_buffer=300))
    st = AccountState(balance=-1500, peak_eod=0)          # $500 left
    d = decide(sig(sl=100), a, st, at(10, 0), False)       # 100 pts × $2 = $200 → 300 left = buffer → blocked
    assert not d.send and "drawdown" in d.reason
    assert decide(sig(sl=50), a, st, at(10, 0), False).send


def test_day_roll_moves_drawdown_anchor():
    st = AccountState(day="2026-10-14", balance=800, peak_eod=0, realized_today=800, trades_today=1)
    decide(sig(), acc(), st, at(10, 0, d=15), False)
    assert st.peak_eod == 800 and st.trades_today == 1 and st.realized_today == 0


def test_copy_trading_multiplier_and_cap():
    a = acc(multiplier=3, rules=Rules(max_contracts=2))
    assert decide(sig(contracts=1), a, AccountState(), at(10, 0), False).qty == 2


# ── server ──
async def _no_news():
    return []


H = {"X-Token": "tok"}


class FakeSender:
    def __init__(self):
        self.calls = []

    async def __call__(self, url, payload):
        self.calls.append((url, payload))
        return 200, "ok"


@pytest.fixture
def client(tmp_path):
    s = Settings(webhook_secret="s3cret", admin_token="tok", dry_run=False, home=str(tmp_path))
    sender = FakeSender()
    b = Bridge(s, [acc(id="a1"), acc(id="a2", multiplier=2), acc(id="off").model_copy(update={"enabled": False})],
               sender=sender, clock=lambda: at(10, 0), news=News(fetch=_no_news))
    c = TestClient(create_app(b))
    c.sender = sender
    return c


def alert(**kw):
    return {"secret": "s3cret", "strategy": "ORB", "symbol": "MNQ1!", "action": "buy", "contracts": "1",
            "position": "long", "price": "20000", "id": "L"} | kw


def test_webhook_fans_out_to_enabled_accounts(client):
    r = client.post("/webhook", json=alert())
    assert r.status_code == 200
    res = {x["account"]: x for x in r.json()["results"]}
    assert res["a1"]["send"] and res["a2"]["send"] and not res["off"]["send"]
    assert [p["quantity"] for _, p in client.sender.calls] == [1, 2]


def test_webhook_rejects_bad_secret_and_duplicates(client):
    assert client.post("/webhook", json=alert(secret="nope")).status_code == 401
    assert client.post("/webhook", json=alert()).json()["results"]
    assert client.post("/webhook", json=alert()).json()["results"] == []     # same alert twice → ignored


def test_dashboard_needs_token(client):
    assert client.get("/api/state").status_code == 401
    assert client.get("/api/state", headers={"X-Token": "nope"}).status_code == 401
    r = client.get("/api/state", headers=H)
    assert r.status_code == 200 and r.json()["setup"]["total"] == 4
    assert client.get("/").status_code == 200


def test_kill_and_flatten(client):
    client.post("/webhook", json=alert())
    client.post("/api/kill?on=true", headers=H)
    r = client.post("/webhook", json=alert(id="L2", price="20010"))
    assert not any(x["send"] for x in r.json()["results"])
    r = client.post("/api/flatten", headers=H).json()["results"]
    assert {x["account"] for x in r} == {"a1", "a2"}
    st = client.get("/api/state", headers=H).json()
    assert all(r["qty"] == 0 for r in st["rows"]) and st["open_positions"] == 0


def test_dry_run_sends_nothing(tmp_path):
    s = Settings(webhook_secret="s3cret", admin_token="tok", dry_run=True, home=str(tmp_path))
    sender = FakeSender()
    c = TestClient(create_app(Bridge(s, [acc()], sender=sender, clock=lambda: at(10, 0), news=News(fetch=_no_news))))
    r = c.post("/webhook", json=alert()).json()["results"]
    assert r[0]["status"] == "dry-run" and sender.calls == []


def test_connections_crud_and_follow(client):
    r = client.post("/api/connections", headers=H, json={"name": "Lucid #2", "group": "evals", "multiplier": 2})
    cid = r.json()["id"]
    assert cid == "lucid-2" and r.json()["enabled"] is False
    assert client.post(f"/api/connections/{cid}/follow?on=true", headers=H).json()["follow"]
    client.put(f"/api/connections/{cid}", headers=H, json={"name": "Lucid #2", "micros_only": True, "rules": {"max_contracts": 5}})
    con = {c["id"]: c for c in client.get("/api/connections", headers=H).json()}
    assert con[cid]["micros_only"] and con[cid]["rules"]["max_contracts"] == 5
    client.post("/api/followers?on=false", headers=H)
    assert not any(c["enabled"] for c in client.get("/api/connections", headers=H).json())
    assert client.delete(f"/api/connections/{cid}", headers=H).json()["ok"]


def test_journal_records_round_trip(client):
    client.post("/webhook", json=alert())
    client.post("/webhook", json=alert(action="sell", position="flat", price="20010", id="X"))
    j = client.get("/api/journal", headers=H).json()
    assert j["stats"]["trades"] == 2 and j["stats"]["net"] == 20 + 40     # a1 ×1, a2 ×2, 10 pts × $2


def test_test_signal_never_sends(client):
    r = client.post("/api/test-signal", headers=H).json()["results"]
    assert {x["status"] for x in r if x["send"]} == {"dry-run"} and client.sender.calls == []
    st = client.get("/api/state", headers=H).json()
    assert st["open_positions"] == 0


def test_health_counts_risk_blocks(client):
    client.post("/api/kill?on=true", headers=H)
    client.post("/webhook", json=alert())
    h = client.get("/api/state", headers=H).json()["health"]
    assert h["protected"] >= 2


def test_settings_toggle_live(client):
    s = client.put("/api/settings", headers=H, json={"dry_run": True, "news_blackout_min": 5}).json()
    assert s["dry_run"] and s["news_blackout_min"] == 5
