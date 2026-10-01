"""SQLite: an event log and the small amount of state that must survive a restart."""
from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import asdict
from datetime import datetime, timezone

from .engine import AccountState


class Store:
    def __init__(self, path: str):
        self._lock = threading.Lock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("create table if not exists events (id integer primary key, ts text, kind text, account text, data text)")
        self.db.execute("create table if not exists kv (k text primary key, v text)")
        self.db.commit()

    def log(self, kind: str, data: dict, account: str = ""):
        with self._lock:
            self.db.execute("insert into events (ts, kind, account, data) values (?, ?, ?, ?)",
                            (datetime.now(timezone.utc).isoformat(timespec="seconds"), kind, account, json.dumps(data)))
            self.db.commit()

    def events(self, limit: int = 100, kinds: tuple[str, ...] = (), since: str = "") -> list[dict]:
        q, args = "select ts, kind, account, data from events where 1=1", []
        if kinds:
            q += f" and kind in ({','.join('?' * len(kinds))})"
            args += list(kinds)
        if since:
            q += " and ts >= ?"
            args.append(since)
        q += " order by id desc limit ?"
        args.append(limit)
        with self._lock:
            rows = self.db.execute(q, args).fetchall()
        return [dict(ts=r[0], kind=r[1], account=r[2], data=json.loads(r[3])) for r in rows]

    def get(self, k: str, default=None):
        with self._lock:
            row = self.db.execute("select v from kv where k = ?", (k,)).fetchone()
        return default if row is None else json.loads(row[0])

    def put(self, k: str, v):
        with self._lock:
            self.db.execute("insert into kv (k, v) values (?, ?) on conflict(k) do update set v = excluded.v", (k, json.dumps(v)))
            self.db.commit()

    def load_state(self, account_id: str) -> AccountState:
        d = self.get(f"state:{account_id}")
        return AccountState(**d) if d else AccountState()

    def save_state(self, account_id: str, st: AccountState):
        self.put(f"state:{account_id}", asdict(st))
