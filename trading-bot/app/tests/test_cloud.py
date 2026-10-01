"""Web edition: accounts, sessions, per-user isolation, webhook routing."""
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bridge.cloud import check_password, create_cloud_app, hash_password  # noqa: E402
from bridge.news import News  # noqa: E402

NY = ZoneInfo("America/New_York")


async def _no_news():
    return []


@pytest.fixture
def app(tmp_path):
    return create_cloud_app(str(tmp_path), bridge_kwargs=dict(clock=lambda: datetime(2026, 10, 15, 10, 0, tzinfo=NY),
                                                             news=News(fetch=_no_news)))


def signup(app, email="a@x.com", pw="password1"):
    c = TestClient(app)
    r = c.post("/auth/signup", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    return c


def test_password_hashing():
    h = hash_password("hunter2hunter2")
    assert h.startswith("scrypt$") and "hunter2" not in h
    assert check_password("hunter2hunter2", h) and not check_password("nope", h)


def test_signup_login_logout(app):
    c = signup(app)
    assert c.get("/api/me").json()["email"] == "a@x.com"
    assert c.get("/api/state").status_code == 200
    c.post("/auth/logout")
    assert c.get("/api/state").status_code == 401
    assert c.post("/auth/login", json={"email": "a@x.com", "password": "wrong-pass"}).status_code == 401
    assert c.post("/auth/login", json={"email": "A@X.com ", "password": "password1"}).status_code == 200
    assert c.get("/api/state").status_code == 200


def test_signup_validation(app):
    c = TestClient(app)
    assert c.post("/auth/signup", json={"email": "bad", "password": "password1"}).status_code == 422
    assert c.post("/auth/signup", json={"email": "b@x.com", "password": "short"}).status_code == 422
    signup(app, "b@x.com")
    assert TestClient(app).post("/auth/signup", json={"email": "b@x.com", "password": "password1"}).status_code == 409


def test_api_needs_login(app):
    c = TestClient(app)
    assert c.get("/api/state").status_code == 401
    assert c.get("/api/connections").status_code == 401
    assert c.get("/api/mode").json()["mode"] == "cloud"


def test_users_are_isolated(app):
    a = signup(app, "a@x.com")
    b = signup(app, "b@x.com")
    a.post("/api/connections", json={"name": "A acct"})
    assert [x["name"] for x in a.get("/api/connections").json()] == ["A acct"]
    assert b.get("/api/connections").json() == []
    sa, sb = a.get("/api/settings").json()["webhook_secret"], b.get("/api/settings").json()["webhook_secret"]
    assert sa and sb and sa != sb


def test_webhook_goes_to_the_owner(app):
    a = signup(app, "a@x.com")
    b = signup(app, "b@x.com")
    a.post("/api/connections", json={"name": "A acct", "template_open": {"q": "{{qty}}"}, "template_close": {"d": "close"}})
    a.post("/api/connections/a-acct/follow?on=true")
    secret = a.get("/api/settings").json()["webhook_secret"]
    anon = TestClient(app)
    r = anon.post("/webhook", json={"secret": secret, "symbol": "MNQ1!", "action": "buy", "position": "long", "price": 20000, "id": "1"})
    assert r.status_code == 200 and r.json()["results"][0]["send"]
    assert any(e["kind"] == "signal" for e in a.get("/api/state").json()["events"])
    assert not any(e["kind"] == "signal" for e in b.get("/api/state").json()["events"])
    assert anon.post("/webhook", json={"secret": "nope", "symbol": "MNQ1!", "action": "buy", "position": "long", "price": 1}).status_code == 401


def test_rate_limit(app):
    c = TestClient(app)
    codes = [c.post("/auth/login", json={"email": "z@x.com", "password": "password1"}).status_code for _ in range(12)]
    assert codes[-1] == 429


def test_pwa_files(app):
    c = TestClient(app)
    assert c.get("/manifest.webmanifest").json()["display"] == "standalone"
    assert "fetch" in c.get("/sw.js").text
