"""Turn a stream of tracked-wallet buys into scored confluence events.

The premise: a single tracked wallet buying something is noise (that is what
the tracker app already spams). Several independent tracked wallets buying the
SAME mint within a short window is the signal.
"""
import time
from collections import defaultdict

import config


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def score_event(event: dict) -> int:
    """0-100. Weighted so that WHO/HOW MANY/HOW FAST dominates, not size."""
    wallets = event["wallet_count"]
    span_min = max(event["span_sec"], 1.0) / 60.0
    sol = event["total_sol"]
    age_min = event["mint_age_sec"] / 60.0

    # How many independent wallets converged (3 -> 0.33, 8+ -> 1.0)
    breadth = _clamp((wallets - config.MIN_WALLETS + 1) / 6.0)
    # How tightly packed in time (all within 1 min -> 1.0, spread over the
    # whole window -> low)
    speed = _clamp(1.0 - (span_min / config.WINDOW_MINUTES))
    # Conviction: total SOL committed (10+ SOL -> 1.0)
    size = _clamp(sol / 10.0)
    # Novelty: the earlier we are relative to when we first saw this mint, the
    # better. Under 5 minutes -> 1.0, over an hour -> ~0.
    novelty = _clamp(1.0 - ((age_min - 5.0) / 55.0)) if age_min > 5 else 1.0

    score = 100 * (0.40 * breadth + 0.25 * speed + 0.15 * size + 0.20 * novelty)
    return int(round(score))


def find_events(store, now: float = None) -> list:
    """Group recent buys by mint and return scored events above threshold."""
    now = now or time.time()
    since = now - config.WINDOW_MINUTES * 60
    by_mint = defaultdict(list)
    for buy in store.buys_in_window(since):
        by_mint[buy["mint"]].append(buy)

    events = []
    for mint, buys in by_mint.items():
        wallets = {b["wallet"] for b in buys}
        if len(wallets) < config.MIN_WALLETS:
            continue
        timestamps = [b["ts"] for b in buys]
        first_seen = store.first_seen(mint) or min(timestamps)
        event = {
            "mint": mint,
            "wallet_count": len(wallets),
            "wallets": sorted(wallets),
            "buy_count": len(buys),
            "total_sol": round(sum(b["sol_spent"] for b in buys), 3),
            "span_sec": max(timestamps) - min(timestamps),
            "first_buy_ts": min(timestamps),
            "last_buy_ts": max(timestamps),
            "mint_age_sec": now - first_seen,
        }
        event["score"] = score_event(event)
        events.append(event)

    events.sort(key=lambda e: e["score"], reverse=True)
    return events


def should_alert(store, event: dict, now: float = None) -> bool:
    """Suppress repeats: same mint only re-alerts on real escalation."""
    if event["score"] < config.MIN_SCORE_TO_ALERT:
        return False
    now = now or time.time()
    previous = store.last_alert(event["mint"])
    if previous is None:
        return True
    if now - previous["ts"] >= config.RE_ALERT_MINUTES * 60:
        return True
    return event["wallet_count"] - previous["wallet_count"] >= config.RE_ALERT_WALLET_DELTA
