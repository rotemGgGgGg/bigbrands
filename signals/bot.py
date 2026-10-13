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

import desk
from broker import OandaBroker, PaperBroker
from parse import parse, risk_reward
from risk import Limits, size

INSTRUMENT = "XAU_USD"


def read_env(path: str = "signals/.env") -> dict:
    out = {}
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
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
        return PaperBroker(env.get("PAPER_DB", "signals/paper.db"))
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


def handle(text: str, env: dict, broker, limits: Limits, live: bool) -> None:
    """One message, start to finish."""
    sig = parse(text)
    if not sig.tradeable:
        desk.signal(env, sig, "skipped", "; ".join(sig.problems))
        notify(env, "⏭ <b>skipped</b>\n" + "\n".join(f"• {p}" for p in sig.problems))
        return

    rr = risk_reward(sig)
    balance = balance_of(broker)
    decision = size(balance, sig.entry, sig.stop, sig.side, limits)
    head = (f"{'🟢' if sig.side == 'buy' else '🔴'} <b>{sig.side.upper()} "
            f"{INSTRUMENT}</b>\n"
            f"entry {sig.entry} · SL {sig.stop} · TP {sig.targets[0]}\n"
            f"risk ${abs(sig.entry - sig.stop):.2f} · R:R {rr}")

    if not decision.allowed:
        desk.signal(env, sig, "skipped", decision.detail)
        notify(env, f"{head}\n\n⛔️ <b>not placed</b>: {decision.detail}")
        return

    fill = broker.market(INSTRUMENT, decision.units, sig.stop, sig.targets[0])
    mode = "LIVE" if live else "PAPER"
    if fill.ok:
        sid = desk.signal(env, sig, "taken", decision.detail)
        desk.opened(env, sid, sig, decision.units, "live" if live else "paper")
        at = f" at {fill.price}" if fill.price else ""
        notify(env, f"{head}\n\n✅ <b>{mode}</b> {decision.units} units{at}\n"
                    f"{decision.detail}\n{fill.detail}")
    else:
        desk.signal(env, sig, "failed", fill.detail)
        notify(env, f"{head}\n\n❌ <b>{mode} failed</b>\n{fill.detail}")


def listen(env: dict, broker, limits: Limits, live: bool) -> None:
    try:
        from telethon import TelegramClient, events
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
    target = int(source) if source.lstrip("-").isdigit() else source

    @client.on(events.NewMessage(chats=target))
    async def on_message(event):
        got = time.strftime("%H:%M:%S")
        print(f"[{got}] message received", flush=True)
        try:
            handle(event.raw_text, env, broker, limits, live)
        except Exception as e:
            # A crash here would silently stop the bot reading, which is
            # worse than a bad trade: nothing would say it had stopped.
            notify(env, f"⚠️ <b>error handling a message</b>\n{e}")

    mode = "LIVE, real orders" if live else "PAPER, nothing sent"
    notify(env, f"👂 <b>listening</b> to {source}\nmode: {mode}")

    async def beat():
        # The desk shows the bot as listening only while this keeps arriving,
        # so a bot that died says so instead of looking merely quiet.
        import asyncio
        while True:
            await asyncio.get_running_loop().run_in_executor(
                None, desk.heartbeat, env, "live" if live else "paper", source)
            await asyncio.sleep(60)

    client.start()
    client.loop.create_task(beat())
    client.run_until_disconnected()


def main() -> None:
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
    limits = Limits(risk_per_trade=args.risk)

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
        print(f"\nrisk per trade    : {100 * limits.risk_per_trade:.2f}% of balance")
        print(f"daily loss cap    : {100 * limits.max_daily_loss:.2f}%")
        print(f"max open at once  : {limits.max_open}")
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
        where = "practice" if broker.practice else "REAL MONEY"
        print(f"live mode on the {where} account", file=sys.stderr)

    if args.replay:
        handle(open(args.replay, encoding="utf-8").read(), env, broker, limits, args.live)
        return

    listen(env, broker, limits, args.live)


if __name__ == "__main__":
    main()
