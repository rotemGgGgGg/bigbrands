"""Alert delivery. Telegram when configured, stdout otherwise."""
import datetime
import html

import requests

import config


def _band(score: int) -> str:
    """Plain-language reading of the score, so the number is not on its own."""
    if score >= 80:
        return "\U0001F534 STRONG"
    if score >= 65:
        return "\U0001F7E0 NOTABLE"
    return "\U0001F7E1 WEAK"


def format_alert(event: dict, wallet_names: dict) -> str:
    mint = event["mint"]
    names = [wallet_names.get(w, w[:4] + "\u2026" + w[-4:]) for w in event["wallets"]]
    span = int(event["span_sec"])
    age = int(event["mint_age_sec"] / 60)
    age_text = "just now" if age < 1 else f"{age} min ago"

    lines = [
        f"{_band(event['score'])}  \u00b7  {event['score']}/100",
        "",
        f"<b>{event['wallet_count']} wallets from your list bought the SAME token</b>",
        f"within {span} seconds of each other.",
        "",
        "<b>Who bought:</b>",
    ]
    lines += [f"  \u2022 {html.escape(n)}" for n in names]
    lines += [
        "",
        f"<b>How much:</b> {event['total_sol']} SOL over {event['buy_count']} buys",
        f"<b>Token first seen:</b> {age_text}",
        "",
        f"<code>{html.escape(mint)}</code>",
        "",
        f'\U0001F4C8 <a href="https://dexscreener.com/solana/{mint}">Chart</a>  \u00b7  '
        f'\U0001F9FE <a href="https://axiom.trade/t/{mint}">Axiom</a>  \u00b7  '
        f'\U0001F50D <a href="https://solscan.io/token/{mint}">Solscan</a>',
        "",
        "<i>This is not a buy signal. It means several wallets you follow "
        "moved on the same thing at the same time \u2014 go look.</i>",
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
