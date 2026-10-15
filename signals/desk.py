"""Reports what the bot did to the desk, the page its owner reads.

Every call here is best effort and never raises. The desk is a record, not a
dependency: if it is unreachable the trade still happens, and the failure is
printed so it is not silently lost.
"""
from __future__ import annotations

import json
import time
import urllib.request


def _post(env: dict, payload: dict) -> dict | None:
    url, key = env.get("DESK_URL"), env.get("DESK_INGEST_KEY")
    if not url or not key:
        return None
    req = urllib.request.Request(
        f"{url.rstrip('/')}/api/event",
        data=json.dumps(payload).encode(),
        # Cloudflare turns away the default Python user agent as a bot.
        headers={"authorization": f"Bearer {key}", "content-type": "application/json",
                 "user-agent": "tape-bot/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.load(r)
    except Exception as e:
        print(f"[desk unreachable: {e}]", flush=True)
        return None


def signal(env: dict, sig, status: str, reason: str | None = None) -> int | None:
    got = _post(env, {
        "type": "signal", "ts": int(time.time()),
        "side": sig.side, "order_type": getattr(sig, "order", None),
        "entry": sig.entry, "sl": sig.stop,
        "tp": sig.targets[0] if sig.targets else None,
        "status": status, "reason": reason, "raw": sig.raw,
    })
    return (got or {}).get("id")


def opened(env: dict, signal_id: int | None, sig, units: int, mode: str,
           fill_price: float | None = None) -> int | None:
    got = _post(env, {
        "type": "open", "ts": int(time.time()), "signal_id": signal_id,
        "side": sig.side, "order_type": getattr(sig, "order", None) or "market",
        "units": abs(units), "entry": fill_price or sig.entry, "sl": sig.stop,
        "tp": sig.targets[0], "mode": mode,
    })
    return (got or {}).get("id")


def closed(env: dict, trade_id: int, exit_price: float, outcome: str) -> None:
    """For live trades, reported by the broker adapter when a position ends."""
    _post(env, {"type": "close", "ts": int(time.time()), "trade_id": trade_id,
                "exit": exit_price, "outcome": outcome})


def heartbeat(env: dict, mode: str, source: str | None, extra: dict | None = None) -> dict:
    """Says the bot is alive, with the account as it stands, and returns what
    the desk wants of it: at present only whether copying is paused."""
    got = _post(env, {"type": "heartbeat", "ts": int(time.time()), "mode": mode,
                      "source": source, **(extra or {})})
    return got or {}


def event(env: dict, ev: dict) -> None:
    """Passes a broker event (fill, expire, close) straight through."""
    _post(env, ev)
