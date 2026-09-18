"""Outcome tracking: snapshot each alerted token's price after the fact.

Without this the thresholds can only be tuned on memory, which remembers the
winners. DexScreener's public API is free and needs no key.
"""
import threading
import time

import requests

SNAPSHOT_OFFSETS = [(15, "15m"), (60, "1h"), (24 * 60, "24h")]
DEXSCREENER = "https://api.dexscreener.com/latest/dex/tokens/{}"

SCHEMA = """
CREATE TABLE IF NOT EXISTS outcomes (
    alert_id  INTEGER NOT NULL,
    mint      TEXT NOT NULL,
    label     TEXT NOT NULL,
    ts        REAL NOT NULL,
    price_usd REAL,
    mcap_usd  REAL,
    liq_usd   REAL,
    PRIMARY KEY (alert_id, label)
);
"""


def fetch_snapshot(mint: str) -> dict:
    try:
        resp = requests.get(DEXSCREENER.format(mint), timeout=15)
        if resp.status_code != 200:
            return {}
        pairs = resp.json().get("pairs") or []
    except (requests.RequestException, ValueError):
        return {}
    if not pairs:
        return {}
    # Most liquid pair is the honest reference price.
    pair = max(pairs, key=lambda p: (p.get("liquidity") or {}).get("usd") or 0)
    return {
        "price_usd": float(pair.get("priceUsd") or 0) or None,
        "mcap_usd": pair.get("marketCap") or pair.get("fdv"),
        "liq_usd": (pair.get("liquidity") or {}).get("usd"),
    }


def _due(conn, now: float):
    """Alerts whose next snapshot window has arrived."""
    rows = conn.execute(
        "SELECT a.id, a.mint, a.ts FROM alerts a WHERE a.ts > ?",
        (now - 26 * 3600,),
    ).fetchall()
    taken = {
        (r["alert_id"], r["label"])
        for r in conn.execute("SELECT alert_id, label FROM outcomes")
    }
    for row in rows:
        for minutes, label in SNAPSHOT_OFFSETS:
            if (row["id"], label) in taken:
                continue
            if now - row["ts"] >= minutes * 60:
                yield row["id"], row["mint"], label


def run(stop_event: threading.Event, interval: int = 60) -> None:
    # The connection must be opened here: SQLite objects belong to the thread
    # that created them.
    import store as store_mod

    store = store_mod.Store()
    store.conn.executescript(SCHEMA)
    store.conn.commit()
    while not stop_event.is_set():
        now = time.time()
        for alert_id, mint, label in list(_due(store.conn, now)):
            snap = fetch_snapshot(mint)
            store.conn.execute(
                "INSERT OR REPLACE INTO outcomes "
                "(alert_id, mint, label, ts, price_usd, mcap_usd, liq_usd) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    alert_id,
                    mint,
                    label,
                    now,
                    snap.get("price_usd"),
                    snap.get("mcap_usd"),
                    snap.get("liq_usd"),
                ),
            )
            store.conn.commit()
            print(f"[followup] {mint[:8]}… {label}: {snap or 'no data'}", flush=True)
        stop_event.wait(interval)


def start() -> threading.Event:
    stop_event = threading.Event()
    thread = threading.Thread(
        target=run, args=(stop_event,), daemon=True, name="followup"
    )
    thread.start()
    return stop_event
