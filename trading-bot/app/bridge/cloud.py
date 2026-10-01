"""Web / multi-user edition: sign up, log in, and every user gets an isolated copier (own connections, rules,
journal, webhook secret). Works from a phone and installs as an app (PWA).

    uvicorn bridge.cloud:create_cloud_app --factory --host 0.0.0.0 --port 8000
    BRIDGE_DATA=/data            where users.db and one folder per user live (default ./data)

Passwords: scrypt with a per-user salt. Sessions: random 32-byte token in an HttpOnly cookie; only its SHA-256 is stored.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import threading
import time
from pathlib import Path

from fastapi import Cookie, HTTPException, Request, Response
from pydantic import BaseModel

from .config import load_settings
from .server import Bridge, build_app

COOKIE = "tb_session"
SESSION_DAYS = 30
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def hash_password(pw: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    dk = hashlib.scrypt(pw.encode(), salt=salt, n=2 ** 14, r=8, p=1, dklen=32)
    return f"scrypt${salt.hex()}${dk.hex()}"


def check_password(pw: str, stored: str) -> bool:
    try:
        _, salt, dk = stored.split("$")
        return hmac.compare_digest(hash_password(pw, bytes.fromhex(salt)).split("$")[2], dk)
    except ValueError:
        return False


class Users:
    def __init__(self, path: str):
        self._lock = threading.Lock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("create table if not exists users (id integer primary key, email text unique not null, "
                        "pw text not null, created real not null)")
        self.db.execute("create table if not exists sessions (token_hash text primary key, user_id integer not null, "
                        "expires real not null)")
        self.db.commit()

    def create(self, email: str, pw: str) -> int:
        with self._lock:
            try:
                cur = self.db.execute("insert into users (email, pw, created) values (?, ?, ?)", (email, hash_password(pw), time.time()))
            except sqlite3.IntegrityError:
                raise HTTPException(409, "An account with this email already exists")
            self.db.commit()
            return cur.lastrowid

    def verify(self, email: str, pw: str) -> int | None:
        with self._lock:
            row = self.db.execute("select id, pw from users where email = ?", (email,)).fetchone()
        if row is None:
            hash_password(pw)                      # same work either way: no timing hint that the email exists
            return None
        return row[0] if check_password(pw, row[1]) else None

    def email(self, uid: int) -> str:
        with self._lock:
            row = self.db.execute("select email from users where id = ?", (uid,)).fetchone()
        return row[0] if row else ""

    def ids(self) -> list[int]:
        with self._lock:
            return [r[0] for r in self.db.execute("select id from users").fetchall()]

    def new_session(self, uid: int) -> str:
        tok = secrets.token_urlsafe(32)
        with self._lock:
            self.db.execute("insert into sessions values (?, ?, ?)",
                            (hashlib.sha256(tok.encode()).hexdigest(), uid, time.time() + SESSION_DAYS * 86400))
            self.db.execute("delete from sessions where expires < ?", (time.time(),))
            self.db.commit()
        return tok

    def session_user(self, tok: str) -> int | None:
        if not tok:
            return None
        with self._lock:
            row = self.db.execute("select user_id, expires from sessions where token_hash = ?",
                                  (hashlib.sha256(tok.encode()).hexdigest(),)).fetchone()
        return row[0] if row and row[1] > time.time() else None

    def end_session(self, tok: str):
        with self._lock:
            self.db.execute("delete from sessions where token_hash = ?", (hashlib.sha256(tok.encode()).hexdigest(),))
            self.db.commit()


class Credentials(BaseModel):
    email: str
    password: str


class RateLimit:
    """At most `n` login/signup attempts per IP per `window` seconds."""
    def __init__(self, n: int = 10, window: int = 300):
        self.n, self.window, self.hits = n, window, {}

    def check(self, key: str):
        now = time.time()
        hits = [t for t in self.hits.get(key, []) if now - t < self.window]
        if len(hits) >= self.n:
            raise HTTPException(429, "Too many attempts — wait a few minutes")
        hits.append(now)
        self.hits[key] = hits


def create_cloud_app(data_dir: str | None = None, bridge_kwargs: dict | None = None):
    data = Path(data_dir or os.environ.get("BRIDGE_DATA", "data"))
    data.mkdir(parents=True, exist_ok=True)
    users = Users(str(data / "users.db"))
    bridges: dict[int, Bridge] = {}
    lock = threading.Lock()
    limiter = RateLimit()
    kw = bridge_kwargs or {}

    def bridge_for(uid: int) -> Bridge:
        with lock:
            if uid not in bridges:
                home = data / "users" / str(uid)
                s = load_settings(str(home), use_env=False)
                bridges[uid] = Bridge(settings=s, **kw)
            return bridges[uid]

    for uid in users.ids():                       # every user's copier runs (webhooks, auto-flatten) without a login
        bridge_for(uid)

    def current(tb_session: str = Cookie(default="")) -> Bridge:
        uid = users.session_user(tb_session)
        if uid is None:
            raise HTTPException(401, "Please log in")
        return bridge_for(uid)

    def find(secret: str) -> Bridge | None:
        for b in list(bridges.values()):
            if b.s.webhook_secret and secrets.compare_digest(secret, b.s.webhook_secret):
                return b
        return None

    app = build_app(lambda: list(bridges.values()), current, find, "cloud")
    app.state.users = users
    app.state.bridges = bridges

    def set_cookie(req: Request, resp: Response, tok: str):
        https = req.url.scheme == "https" or req.headers.get("x-forwarded-proto") == "https"
        resp.set_cookie(COOKIE, tok, max_age=SESSION_DAYS * 86400, httponly=True, samesite="lax", secure=https, path="/")

    def clean(c: Credentials) -> tuple[str, str]:
        email = c.email.strip().lower()
        if not EMAIL_RE.match(email) or len(email) > 200:
            raise HTTPException(422, "Enter a valid email")
        if len(c.password) < 8 or len(c.password) > 200:
            raise HTTPException(422, "Password must be at least 8 characters")
        return email, c.password

    @app.post("/auth/signup")
    def signup(c: Credentials, req: Request, resp: Response):
        limiter.check(req.client.host if req.client else "?")
        email, pw = clean(c)
        uid = users.create(email, pw)
        bridge_for(uid)
        set_cookie(req, resp, users.new_session(uid))
        return {"email": email}

    @app.post("/auth/login")
    def login(c: Credentials, req: Request, resp: Response):
        limiter.check(req.client.host if req.client else "?")
        uid = users.verify(c.email.strip().lower(), c.password)
        if uid is None:
            raise HTTPException(401, "Wrong email or password")
        set_cookie(req, resp, users.new_session(uid))
        return {"email": users.email(uid)}

    @app.post("/auth/logout")
    def logout(resp: Response, tb_session: str = Cookie(default="")):
        if tb_session:
            users.end_session(tb_session)
        resp.delete_cookie(COOKIE, path="/")
        return {"ok": True}

    @app.get("/api/me")
    def me(tb_session: str = Cookie(default="")):
        uid = users.session_user(tb_session)
        if uid is None:
            raise HTTPException(401, "Please log in")
        return {"email": users.email(uid)}

    return app
