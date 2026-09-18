"""Alert delivery. Telegram when configured, stdout otherwise."""
import datetime
import html

import requests

import config


def format_alert(event: dict, wallet_names: dict) -> str:
    mint = event["mint"]
    names = [wallet_names.get(w, w[:4] + "…" + w[-4:]) for w in event["wallets"]]
    span = int(event["span_sec"])
    age = int(event["mint_age_sec"] / 60)
    when = datetime.datetime.now().strftime("%H:%M:%S")

    lines = [
        f"<b>SIGNAL {event['score']}/100</b>  ·  {when}",
        f"<code>{html.escape(mint)}</code>",
        "",
        f"<b>{event['wallet_count']} tracked wallets</b> bought within {span}s",
        "· " + html.escape(", ".join(names)),
        "",
        f"Buys: {event['buy_count']}  |  Total: {event['total_sol']} SOL",
        f"First seen by radar: {age}m ago",
        "",
        f'<a href="https://dexscreener.com/solana/{mint}">DexScreener</a> · '
        f'<a href="https://axiom.trade/t/{mint}">Axiom</a> · '
        f'<a href="https://solscan.io/token/{mint}">Solscan</a>',
    ]
    return "\n".join(lines)


def send(text: str) -> bool:
    """Returns True if the message was delivered to Telegram."""
    if not (config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID):
        print("\n" + "=" * 60)
        print(_strip_html(text))
        print("=" * 60 + "\n", flush=True)
        return False
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(
            url,
            json={
                "chat_id": config.TELEGRAM_CHAT_ID,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=15,
        )
        if resp.status_code != 200:
            print(f"[telegram] failed {resp.status_code}: {resp.text[:200]}", flush=True)
            return False
        return True
    except requests.RequestException as exc:
        print(f"[telegram] error: {exc}", flush=True)
        return False


def _strip_html(text: str) -> str:
    import re

    text = re.sub(r"<a href=\"([^\"]+)\">([^<]+)</a>", r"\2: \1", text)
    return html.unescape(re.sub(r"<[^>]+>", "", text))
