"""SQLite persistence: wallet cursors, observed buys, fired alerts."""
import json
import sqlite3
import time
from typing import Iterable, Optional

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS wallet_cursor (
    address     TEXT PRIMARY KEY,
    last_sig    TEXT,
    updated_at  REAL,
    last_active REAL
);
CREATE TABLE IF NOT EXISTS buys (
    sig        TEXT NOT NULL,
    wallet     TEXT NOT NULL,
    mint       TEXT NOT NULL,
    ts         REAL NOT NULL,
    sol_spent  REAL NOT NULL,
    amount     REAL NOT NULL,
    PRIMARY KEY (sig, wallet, mint)
);
CREATE INDEX IF NOT EXISTS idx_buys_mint_ts ON buys (mint, ts);
CREATE TABLE IF NOT EXISTS mint_seen (
    mint       TEXT PRIMARY KEY,
    first_seen REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS alerts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    mint         TEXT NOT NULL,
    ts           REAL NOT NULL,
    score        INTEGER NOT NULL,
    wallet_count INTEGER NOT NULL,
    payload      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_alerts_mint_ts ON alerts (mint, ts);
"""


class Store:
    def __init__(self, path=None):
        self.conn = sqlite3.connect(str(path or config.DB_PATH))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # -- cursors ------------------------------------------------------------
    def get_cursor(self, address: str) -> Optional[str]:
        row = self.conn.execute(
            "SELECT last_sig FROM wallet_cursor WHERE address = ?", (address,)
        ).fetchone()
        return row["last_sig"] if row else None

    def set_cursor(self, address: str, last_sig: str) -> None:
        self.conn.execute(
            "INSERT INTO wallet_cursor (address, last_sig, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(address) DO UPDATE SET last_sig = excluded.last_sig, "
            "updated_at = excluded.updated_at",
            (address, last_sig, time.time()),
        )
        self.conn.commit()

    def has_cursor(self, address: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM wallet_cursor WHERE address = ?", (address,)
        ).fetchone()
        return row is not None

    def set_last_active(self, address: str, ts: float) -> None:
        self.conn.execute(
            "UPDATE wallet_cursor SET last_active = ? WHERE address = ?", (ts, address)
        )
        self.conn.commit()

    def stale_addresses(self, older_than_ts: float) -> set:
        """Wallets whose newest transaction predates the cutoff."""
        return {
            r["address"]
            for r in self.conn.execute(
                "SELECT address FROM wallet_cursor WHERE last_active IS NOT NULL "
                "AND last_active < ?",
                (older_than_ts,),
            )
        }

    # -- buys ---------------------------------------------------------------
    def record_buys(self, rows: Iterable[dict]) -> int:
        rows = list(rows)
        if not rows:
            return 0
        self.conn.executemany(
            "INSERT OR IGNORE INTO buys (sig, wallet, mint, ts, sol_spent, amount) "
            "VALUES (:sig, :wallet, :mint, :ts, :sol_spent, :amount)",
            rows,
        )
        self.conn.executemany(
            "INSERT OR IGNORE INTO mint_seen (mint, first_seen) VALUES (?, ?)",
            [(r["mint"], r["ts"]) for r in rows],
        )
        self.conn.commit()
        return len(rows)

    def buys_in_window(self, since_ts: float) -> list:
        return [
            dict(r)
            for r in self.conn.execute(
                "SELECT * FROM buys WHERE ts >= ? ORDER BY ts", (since_ts,)
            )
        ]

    def first_seen(self, mint: str) -> Optional[float]:
        row = self.conn.execute(
            "SELECT first_seen FROM mint_seen WHERE mint = ?", (mint,)
        ).fetchone()
        return row["first_seen"] if row else None

    def prune_buys(self, older_than_ts: float) -> None:
        self.conn.execute("DELETE FROM buys WHERE ts < ?", (older_than_ts,))
        self.conn.commit()

    # -- alerts -------------------------------------------------------------
    def last_alert(self, mint: str) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT * FROM alerts WHERE mint = ? ORDER BY ts DESC LIMIT 1", (mint,)
        ).fetchone()
        return dict(row) if row else None

    def record_alert(self, mint: str, score: int, wallet_count: int, payload: dict) -> int:
        cur = self.conn.execute(
            "INSERT INTO alerts (mint, ts, score, wallet_count, payload) VALUES (?, ?, ?, ?, ?)",
            (mint, time.time(), score, wallet_count, json.dumps(payload, ensure_ascii=False)),
        )
        self.conn.commit()
        return cur.lastrowid

    def close(self) -> None:
        self.conn.close()
