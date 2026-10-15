"""The bot: read the channel, parse the signal, size it, place it, say so.

Everything here is wired and testable except the channel itself, which needs
a login only the account's owner can do. Until then `--replay` feeds it a
message from a file and the whole path runs, so the thing being connected
later is a reader, not an unknown.

It defaults to paper. The question of whether these signals make money is
not yet answered, and `--live` is the one setting that stops asking it.

    python3 signals/bot.py --replay message.txt     # whole path, no account
    python3 signals/bot.py --check                  # what is configured
    python3 signals/bot.py                          # listen (needs TG_SESSION)
    python3 signals/bot.py --live                   # send real orders
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import desk
from broker import OandaBroker, PaperBroker
from parse import parse, risk_reward
from risk import Limits, size

INSTRUMENT = "XAU_USD"


HERE = os.path.dirname(os.path.abspath(__file__))


def read_env(path: str | None = None) -> dict:
    # Next to this file rather than relative to wherever it was started from,
    # and tolerant of the byte-order mark Windows tools put at the top.
    path = path or os.path.join(HERE, ".env")
    out = {}
    if os.path.exists(path):
        for line in open(path, encoding="utf-8-sig"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    return out


def notify(env: dict, text: str) -> None:
    """Tells the owner what happened. Never raises: a failed message must not
    take down the bot, and a placed order has to be reported even if the
    reporting channel is down — so the failure goes to the log too."""
    token, chat = env.get("TG_BOT_TOKEN"), env.get("TG_BOT_CHAT")
    print(text, flush=True)
    if not token or not chat:
        return
    try:
        body = urllib.parse.urlencode({
            "chat_id": chat, "text": text, "parse_mode": "HTML",
            "disable_web_page_preview": "true"}).encode()
        urllib.request.urlopen(
            f"https://api.telegram.org/bot{token}/sendMessage", body, timeout=10)
    except Exception as e:
        print(f"[notify failed: {e}]", flush=True)


def make_broker(env: dict, live: bool):
    if not live:
        return PaperBroker(env.get("PAPER_DB") or os.path.join(HERE, "paper.db"))
    if env.get("BROKER", "").lower() == "mt5":
        from broker_mt5 import Mt5Broker
        return Mt5Broker(symbol=env.get("MT5_SYMBOL") or None,
                         allow_real=env.get("ALLOW_REAL", "").lower() == "yes",
                         track_path=os.path.join(HERE, "tracked.json"),
                         start_balance=float(env["ACCOUNT_START"]) if env.get("ACCOUNT_START") else None,
                         be_at_r=float(env.get("BE_AT_R", "1.5")) or None,
                         be_plus_usd=float(env.get("BE_PLUS_USD", "1")))
    token, account = env.get("OANDA_TOKEN"), env.get("OANDA_ACCOUNT")
    if not token or not account:
        raise SystemExit("--live needs OANDA_TOKEN and OANDA_ACCOUNT in signals/.env")
    practice = env.get("OANDA_PRACTICE", "true").lower() != "false"
    return OandaBroker(token, account, practice=practice)


def balance_of(broker) -> float:
    """The live balance, or a stated figure for paper so sizing is realistic."""
    if isinstance(broker, PaperBroker):
        return float(os.environ.get("PAPER_BALANCE", "10000"))
    s = broker.summary()
    if "__error__" in s:
        raise SystemExit(f"cannot read the account: {json.dumps(s['__error__'])[:300]}")
    return float(s["account"]["balance"])


# Set from the desk: a paused bot still reads and records every signal, it
# just places nothing. Reading on is what lets the record show what a pause
# cost or saved.
CONTROL = {"paused": False, "halt": None}

# A limit reached stops copying until the owner presses resume on the desk:
# the guard alone would start again by itself the next day. Each limit stops
# it once per day (the account limit once for good), so a resume is not undone
# by the next signal that runs into the same, already acknowledged, limit.
LATCH_PATH = Path(__file__).with_name("latch.json")


def _latched() -> set:
    try:
        return set(json.loads(LATCH_PATH.read_text()))
    except Exception:
        return set()


def halt(env: dict, key: str, why: str) -> None:
    seen = _latched()
    if key in seen:
        return
    LATCH_PATH.write_text(json.dumps(sorted(seen | {key})))
    CONTROL["paused"] = True
    CONTROL["halt"] = why          # carried by the heartbeats until the desk has it
    print(f"STOPPED: {why}", flush=True)
    notify(env, f"🛑 <b>STOPPED</b>: {why}\nNothing more is placed until you press "
                f"<b>Resume copying</b> on the desk.")


def limit_key(detail: str) -> str | None:
    """Which limit a refusal ran into, as a latch key, or None for any other."""
    day = time.strftime("%Y-%m-%d", time.gmtime())
    for prefix, key in (("daily cap", f"daily:{day}"), ("day limit", f"trades:{day}"),
                        ("total cap", "total")):
        if detail.startswith(prefix):
            return key
    return None


def handle(text: str, env: dict, broker, limits: Limits, live: bool) -> None:
    """One message, start to finish."""
    sig = parse(text)
    if sig.tradeable and CONTROL["paused"]:
        desk.signal(env, sig, "skipped", "copying paused")
        notify(env, "⏸ <b>signal skipped</b>: copying is paused; Resume copying on the desk starts it again")
        return
    if not sig.tradeable:
        desk.signal(env, sig, "skipped", "; ".join(sig.problems))
        notify(env, "⏭ <b>skipped</b>\n" + "\n".join(f"• {p}" for p in sig.problems))
        return

    rr = risk_reward(sig)
    if hasattr(broker, "state"):
        # The account as it stands, so the caps see today's losses and
        # everything already open before adding to it.
        state = broker.state()
        decision = size(state.balance, sig.entry, sig.stop, sig.side, limits, state=state)
    else:
        decision = size(balance_of(broker), sig.entry, sig.stop, sig.side, limits)
    head = (f"{'🟢' if sig.side == 'buy' else '🔴'} <b>{sig.side.upper()} "
            f"{INSTRUMENT}</b>\n"
            f"entry {sig.entry} · SL {sig.stop} · TP {sig.targets[0]}\n"
            f"risk ${abs(sig.entry - sig.stop):.2f} · R:R {rr}")

    if not decision.allowed:
        desk.signal(env, sig, "skipped", decision.detail)
        notify(env, f"{head}\n\n⛔️ <b>not placed</b>: {decision.detail}")
        key = limit_key(decision.detail)
        if key:
            halt(env, key, decision.detail)
        return

    fill = broker.place(sig, decision.units)
    mode = "LIVE" if live else "PAPER"
    if fill.ok:
        sid = desk.signal(env, sig, "taken", decision.detail)
        tid = desk.opened(env, sid, sig, decision.units, "live" if live else "paper",
                          fill_price=fill.price if (getattr(sig, "order", None) or "market") == "market" else None)
        if tid and fill.order_id and hasattr(broker, "track"):
            broker.track(tid, fill.order_id,
                         pending=(getattr(sig, "order", None) or "market") != "market",
                         side=sig.side, stop=sig.stop)
        at = f" at {fill.price}" if fill.price else ""
        notify(env, f"{head}\n\n✅ <b>{mode}</b> {decision.units} units{at}\n"
                    f"{decision.detail}\n{fill.detail}")
    else:
        desk.signal(env, sig, "failed", fill.detail)
        notify(env, f"{head}\n\n❌ <b>{mode} failed</b>\n{fill.detail}")


def listen(env: dict, broker, limits: Limits, live: bool) -> None:
    try:
        from telethon import TelegramClient, events  # noqa: F401
        from telethon.sessions import StringSession
    except ImportError:
        raise SystemExit("pip install telethon")

    session = env.get("TG_SESSION")
    source = env.get("TG_SOURCE")
    if not session:
        raise SystemExit("no TG_SESSION — run: python3 signals/login.py")
    if not source:
        raise SystemExit("no TG_SOURCE — run login.py to list the channels")

    client = TelegramClient(StringSession(session),
                            int(env["TG_API_ID"]), env["TG_API_HASH"])
    client.start()
    if source.lstrip("-").isdigit():
        target = int(source)
    elif source.startswith("@"):
        target = source
    else:
        # A title: a channel just created has no ID anyone has looked up yet.
        target = next((d.id for d in client.iter_dialogs() if d.name == source), None)
        if target is None:
            raise SystemExit(f"no channel or group named {source!r} on this account")

    @client.on(events.NewMessage(chats=target))
    async def on_message(event):
        lag = time.time() - event.message.date.timestamp()
        print(f"[{time.strftime('%H:%M:%S')}] message received, "
              f"{lag:.1f}s after it was posted", flush=True)
        try:
            handle(event.raw_text, env, broker, limits, live)
        except Exception as e:
            # A crash here would silently stop the bot reading, which is
            # worse than a bad trade: nothing would say it had stopped.
            notify(env, f"⚠️ <b>error handling a message</b>\n{e}")

    mode = "LIVE, real orders" if live else "PAPER, nothing sent"
    notify(env, f"👂 <b>listening</b> to {source}\nmode: {mode}")

    def account_snapshot() -> dict:
        snap = {"rules": {
            "risk_usd": limits.risk_usd, "daily_stop_usd": limits.daily_stop_usd,
            "total_stop_usd": limits.total_stop_usd, "max_open": limits.max_open,
            "max_trades_day": limits.max_trades_day,
            "be_at_r": float(env.get("BE_AT_R", "1.5")), "be_plus_usd": float(env.get("BE_PLUS_USD", "1")),
        }}
        if hasattr(broker, "state"):
            try:
                st = broker.state()
                acc = broker.account
                snap["account"] = {
                    "balance": st.balance, "equity": st.equity, "day_loss": st.day_loss,
                    "total_loss": st.total_loss, "open_risk": st.open_risk,
                    "open_count": st.open_count, "trades_today": st.trades_today, "start": broker.start_balance,
                    "login": str(acc.login), "server": acc.server, "demo": broker.demo,
                    "name": getattr(acc, "name", ""), "firm": env.get("ACCOUNT_LABEL", ""),
                }
                # Losses that reach a limit stop copying even with no new
                # signal to run into it, floating losses included.
                day = time.strftime("%Y-%m-%d", time.gmtime())
                if limits.daily_stop_usd and st.day_loss >= limits.daily_stop_usd:
                    halt(env, f"daily:{day}", f"daily stop: ${st.day_loss:.2f} lost today, "
                                              f"the limit is ${limits.daily_stop_usd:.2f}")
                if limits.total_stop_usd and st.total_loss >= limits.total_stop_usd:
                    halt(env, "total", f"account stop: ${st.total_loss:.2f} below the start, "
                                       f"the limit is ${limits.total_stop_usd:.2f}")
            except Exception as e:
                print(f"[account snapshot failed: {e}]", flush=True)
        return snap

    async def beat():
        # The desk shows the bot as listening only while this keeps arriving,
        # so a bot that died says so instead of looking merely quiet. Each
        # beat carries the account and brings back the desk's instructions.
        import asyncio
        loop = asyncio.get_running_loop()
        while True:
            def send():
                snap = account_snapshot()
                if CONTROL["halt"]:
                    snap["halt"] = CONTROL["halt"]
                return desk.heartbeat(env, "live" if live else "paper", source, snap)
            got = await loop.run_in_executor(None, send)
            if CONTROL["halt"] and got.get("paused"):
                CONTROL["halt"] = None    # the desk has it, and shows it
            if "paused" in got and bool(got["paused"]) != CONTROL["paused"]:
                CONTROL["paused"] = bool(got["paused"])
                notify(env, "⏸ <b>copying paused</b> from the desk" if CONTROL["paused"]
                       else "▶️ <b>copying resumed</b> from the desk")
            await asyncio.sleep(30)

    client.loop.create_task(beat())

    if hasattr(broker, "poll"):
        async def follow():
            # The broker closes positions at their stop or target on its own;
            # this notices, and tells the desk and the owner what happened.
            import asyncio
            loop = asyncio.get_running_loop()
            while True:
                try:
                    for ev in await loop.run_in_executor(None, broker.poll):
                        desk.event(env, ev)
                        if ev["type"] == "close":
                            notify(env, f"{'✅' if ev['outcome'] == 'tp' else '🛑' if ev['outcome'] == 'sl' else '✋'} "
                                        f"<b>closed</b> at {ev['exit']} ({ev['outcome']}), "
                                        f"{ev.get('profit', 0):+.2f}")
                        elif ev["type"] == "fill":
                            notify(env, f"📥 <b>pending order filled</b> at {ev['entry']}")
                        elif ev["type"] == "expire":
                            notify(env, "⌛ <b>pending order expired</b> without filling")
                        elif ev["type"] == "be":
                            notify(env, f"🔒 <b>stop moved to break-even</b> ({ev['sl']})")
                except Exception as e:
                    print(f"[follow error: {e}]", flush=True)
                await asyncio.sleep(15)
        client.loop.create_task(follow())
    client.run_until_disconnected()


def main() -> None:
    # A Windows console defaults to a code page that cannot print emoji, and
    # every message this bot echoes has them. Without this the first signal
    # would crash it.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true",
                    help="place real orders instead of recording them")
    ap.add_argument("--replay", metavar="FILE",
                    help="run one message from a file through the whole path")
    ap.add_argument("--check", action="store_true", help="show what is configured")
    ap.add_argument("--risk", type=float, default=0.005,
                    help="fraction of balance risked per trade (default 0.005)")
    args = ap.parse_args()

    env = read_env()
    num = lambda k: float(env[k]) if env.get(k) else None
    limits = Limits(risk_per_trade=args.risk,
                    risk_usd=num("RISK_USD"),
                    daily_stop_usd=num("DAILY_STOP_USD"),
                    total_stop_usd=num("TOTAL_STOP_USD"),
                    max_open=int(env.get("MAX_OPEN", "2")),
                    max_trades_day=int(env["MAX_TRADES_DAY"]) if env.get("MAX_TRADES_DAY") else None)

    if args.check:
        have = lambda k: "set" if env.get(k) else "MISSING"
        print("telegram api id   :", have("TG_API_ID"))
        print("telegram api hash :", have("TG_API_HASH"))
        print("telegram session  :", have("TG_SESSION"), "  (run login.py)")
        print("channel to read   :", env.get("TG_SOURCE") or "MISSING")
        print("bot token (alerts):", have("TG_BOT_TOKEN"))
        print("oanda token       :", have("OANDA_TOKEN"))
        print("oanda account     :", env.get("OANDA_ACCOUNT") or "MISSING")
        print("spot price key    :", have("TWELVEDATA_KEY"))
        print(f"\nrisk per trade    : " + (f"${limits.risk_usd:.2f}" if limits.risk_usd
                                         else f"{100 * limits.risk_per_trade:.2f}% of balance"))
        print(f"daily stop        : " + (f"${limits.daily_stop_usd:.2f}" if limits.daily_stop_usd else "not set"))
        print(f"total stop        : " + (f"${limits.total_stop_usd:.2f}" if limits.total_stop_usd else "not set"))
        print(f"max open at once  : {limits.max_open}")
        print(f"max trades a day  : {limits.max_trades_day or 'no limit'}")
        print(f"break-even        : at {env.get('BE_AT_R', '1.5')}R, stop to entry + ${env.get('BE_PLUS_USD', '1')}")
        if env.get("OANDA_TOKEN") and env.get("OANDA_ACCOUNT"):
            b = make_broker(env, live=True)
            s = b.summary()
            if "__error__" in s:
                print("\noanda says        :", json.dumps(s["__error__"])[:200])
            else:
                acc = s["account"]
                print(f"\nbalance           : {acc['balance']} {acc['currency']}")
                print("gold tradeable    :", b.tradeable(INSTRUMENT))
        return

    broker = make_broker(env, args.live)
    if args.live:
        if not broker.tradeable(INSTRUMENT):
            raise SystemExit(f"this account cannot trade {INSTRUMENT}")
        where = broker.describe() if hasattr(broker, "describe") else \
            ("practice account" if broker.practice else "REAL MONEY account")
        print(f"live mode: {where}", flush=True)

    if args.replay:
        handle(open(args.replay, encoding="utf-8").read(), env, broker, limits, args.live)
        return

    single_instance()
    listen(env, broker, limits, args.live)


def single_instance() -> None:
    """Refuses to start a second copy. Two copies on one account would place
    every signal twice, at twice the risk. Holding a local port is the lock:
    the system frees it the moment this process ends, however it ends."""
    import socket
    global _LOCK
    _LOCK = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        _LOCK.bind(("127.0.0.1", 47321))
    except OSError:
        print("another copy of the bot is already running; this one stops", flush=True)
        sys.exit(3)


if __name__ == "__main__":
    main()
