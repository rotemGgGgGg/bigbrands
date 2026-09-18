"""Wallet-confluence radar.

Loop: walk the tracked wallets, pull their new transactions, keep the buys, and
alert when several independent wallets land on the same mint inside a short
window.
"""
import argparse
import datetime
import signal
import sys
import time

import config
import confluence
import notify
import solana
import store as store_mod
import wallets as wallets_mod

RUNNING = True


def _stop(signum, frame):
    global RUNNING
    RUNNING = False
    print("\n[radar] stopping…", flush=True)


def log(msg: str) -> None:
    print(f"[{datetime.datetime.now():%H:%M:%S}] {msg}", flush=True)


def bootstrap(rpc, store, wallet_list) -> None:
    """Record the current newest signature per wallet so we only look forward.

    Also prints last-activity stats, which come free with the same call.
    """
    pending = [w for w in wallet_list if not store.has_cursor(w["address"])]
    if not pending:
        return
    log(f"bootstrapping {len(pending)} wallets (one RPC call each)…")
    now = time.time()
    buckets = {"<1d": 0, "<7d": 0, "<30d": 0, "older": 0, "never": 0}
    for i, wallet in enumerate(pending, 1):
        try:
            sigs = rpc.get_signatures(wallet["address"], limit=1)
        except solana.RpcError as exc:
            log(f"  ! {wallet['name']}: {exc}")
            continue
        if not sigs:
            buckets["never"] += 1
            store.set_cursor(wallet["address"], "")
            continue
        store.set_cursor(wallet["address"], sigs[0]["signature"])
        block_time = sigs[0].get("blockTime") or now
        store.set_last_active(wallet["address"], block_time)
        age = now - block_time
        if age < 86400:
            buckets["<1d"] += 1
        elif age < 7 * 86400:
            buckets["<7d"] += 1
        elif age < 30 * 86400:
            buckets["<30d"] += 1
        else:
            buckets["older"] += 1
        if i % 50 == 0:
            log(f"  {i}/{len(pending)}")
    log(f"wallet last-activity: {buckets}")


def scan_wallet(rpc, store, wallet) -> int:
    """Fetch new transactions for one wallet and store any buys found."""
    address = wallet["address"]
    cursor = store.get_cursor(address) or None
    try:
        sigs = rpc.get_signatures(address, until=cursor or None, limit=25)
    except solana.RpcError as exc:
        log(f"  ! sigs {wallet['name']}: {exc}")
        return 0
    if not sigs:
        return 0

    newest = sigs[0]["signature"]
    found = 0
    errors = 0
    for entry in reversed(sigs):  # oldest first
        if entry.get("err"):
            continue
        try:
            tx = rpc.get_transaction(entry["signature"])
        except solana.RpcError as exc:
            errors += 1
            last_error = exc
            continue
        buys = solana.extract_buys(tx, address)
        if not buys:
            continue
        ts = entry.get("blockTime") or time.time()
        found += store.record_buys(
            [
                {
                    "sig": entry["signature"],
                    "wallet": address,
                    "mint": b["mint"],
                    "ts": ts,
                    "sol_spent": round(b["sol_spent"], 4),
                    "amount": b["amount"],
                }
                for b in buys
            ]
        )
    if errors:
        log(f"  ! {wallet['name']}: {errors} tx fetch errors ({last_error})")
    store.set_cursor(address, newest)
    return found


def check_and_alert(store, names) -> None:
    for event in confluence.find_events(store):
        if not confluence.should_alert(store, event):
            continue
        text = notify.format_alert(event, names)
        delivered = notify.send(text)
        store.record_alert(event["mint"], event["score"], event["wallet_count"], event)
        log(
            f"ALERT {event['score']}/100 {event['mint'][:8]}… "
            f"({event['wallet_count']} wallets)" + ("" if delivered else " [stdout]")
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Tracked-wallet confluence radar")
    parser.add_argument("--dry-run", action="store_true", help="print alerts instead of sending to Telegram")
    parser.add_argument("--bootstrap-only", action="store_true", help="set cursors and exit")
    parser.add_argument("--once", action="store_true", help="single pass over all wallets, then exit")
    args = parser.parse_args()

    if args.dry_run:
        config.TELEGRAM_BOT_TOKEN = ""

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    wallet_list = wallets_mod.load_wallets()
    names = wallets_mod.name_map(wallet_list)
    store = store_mod.Store()
    rpc = solana.SolanaRpc()

    log(f"tracking {len(wallet_list)} wallets · rpc {config.RPC_URL.split('?')[0]} @ {config.RPC_RPS}/s")
    log(
        f"rule: >={config.MIN_WALLETS} wallets on one mint within {config.WINDOW_MINUTES}m, "
        f"score >= {config.MIN_SCORE_TO_ALERT}"
    )

    bootstrap(rpc, store, wallet_list)
    if args.bootstrap_only:
        store.close()
        return 0

    if config.SKIP_STALE_DAYS:
        stale = store.stale_addresses(time.time() - config.SKIP_STALE_DAYS * 86400)
        active = [w for w in wallet_list if w["address"] not in stale]
        if active:
            log(
                f"skipping {len(wallet_list) - len(active)} wallets idle > "
                f"{config.SKIP_STALE_DAYS}d · scanning {len(active)}"
            )
            wallet_list = active

    index = 0
    last_check = 0.0
    last_prune = time.time()
    pass_start = time.time()
    buys_this_pass = 0

    while RUNNING:
        wallet = wallet_list[index]
        buys_this_pass += scan_wallet(rpc, store, wallet)
        index += 1

        if index >= len(wallet_list):
            log(
                f"pass complete in {int(time.time() - pass_start)}s · "
                f"{buys_this_pass} buys recorded"
            )
            index = 0
            pass_start = time.time()
            buys_this_pass = 0
            if args.once:
                break

        now = time.time()
        if now - last_check >= config.CHECK_INTERVAL_SEC:
            check_and_alert(store, names)
            last_check = now
        if now - last_prune >= 3600:
            store.prune_buys(now - 24 * 3600)
            last_prune = now

    check_and_alert(store, names)
    store.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
