"""Telegram chat bot that answers with Claude.

Reads config.json from the folder the .exe (or this script) lives in.
Runs until the window is closed; the bot is offline while it isn't running.
"""

import json
import os
import sys
import time

import anthropic
import requests

MODEL = "claude-opus-5-5"
MAX_HISTORY_MESSAGES = 40  # start a fresh conversation after this many turns
TELEGRAM_LIMIT = 4096

SYSTEM_PROMPT = (
    "You are a helpful assistant chatting with the user over Telegram. "
    "Reply in the same language the user writes in. Keep answers short and "
    "plain - Telegram shows raw text, so avoid markdown tables and headings."
)


def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def load_config():
    path = os.path.join(app_dir(), "config.json")
    if not os.path.exists(path):
        print(f"Missing {path}. Copy config.example.json to config.json and fill it in.")
        input("Press Enter to exit...")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class Telegram:
    def __init__(self, token):
        self.base = f"https://api.telegram.org/bot{token}"

    def get_updates(self, offset):
        r = requests.get(
            f"{self.base}/getUpdates",
            params={"offset": offset, "timeout": 30},
            timeout=40,
        )
        r.raise_for_status()
        return r.json()["result"]

    def send(self, chat_id, text):
        text = text or "(empty reply)"
        for i in range(0, len(text), TELEGRAM_LIMIT):
            requests.post(
                f"{self.base}/sendMessage",
                json={"chat_id": chat_id, "text": text[i : i + TELEGRAM_LIMIT]},
                timeout=30,
            )

    def typing(self, chat_id):
        requests.post(
            f"{self.base}/sendChatAction",
            json={"chat_id": chat_id, "action": "typing"},
            timeout=10,
        )


def ask_claude(client, history):
    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        output_config={"effort": "low"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=history,
    )
    if response.stop_reason == "refusal":
        return response, None
    text = "".join(b.text for b in response.content if b.type == "text")
    return response, text


def main():
    config = load_config()
    telegram = Telegram(config["telegram_bot_token"])
    client = anthropic.Anthropic(api_key=config["anthropic_api_key"])
    allowed = {int(u) for u in config.get("allowed_user_ids", [])}

    histories = {}  # chat_id -> list of messages
    offset = 0
    print("Bot is running. Close this window to stop it.")

    while True:
        try:
            updates = telegram.get_updates(offset)
        except requests.RequestException as e:
            print(f"Telegram connection error: {e}. Retrying in 5s...")
            time.sleep(5)
            continue

        for update in updates:
            offset = update["update_id"] + 1
            msg = update.get("message")
            if not msg or "text" not in msg:
                continue

            chat_id = msg["chat"]["id"]
            user_id = msg["from"]["id"]
            text = msg["text"]

            if allowed and user_id not in allowed:
                telegram.send(chat_id, f"Not authorized. Your user id is {user_id}.")
                print(f"Blocked message from user {user_id}")
                continue

            if text.strip() in ("/start", "/reset"):
                histories.pop(chat_id, None)
                telegram.send(chat_id, "New conversation started. Send me anything.")
                continue

            history = histories.setdefault(chat_id, [])
            if len(history) >= MAX_HISTORY_MESSAGES:
                history.clear()
            history.append({"role": "user", "content": text})

            print(f"[{user_id}] {text}")
            telegram.typing(chat_id)
            try:
                response, reply = ask_claude(client, history)
            except anthropic.AuthenticationError:
                history.pop()
                telegram.send(chat_id, "Bad Anthropic API key - check config.json.")
                continue
            except anthropic.RateLimitError:
                history.pop()
                telegram.send(chat_id, "Rate limited, try again in a minute.")
                continue
            except (anthropic.APIStatusError, anthropic.APIConnectionError) as e:
                history.pop()
                print(f"Claude error: {e}")
                telegram.send(chat_id, "Error talking to Claude, try again.")
                continue

            if reply is None:
                history.pop()  # don't keep a refused turn in the history
                telegram.send(chat_id, "I can't help with that one.")
                continue

            # Keep the full content (including thinking blocks) so the history stays valid.
            history.append({"role": "assistant", "content": response.content})
            telegram.send(chat_id, reply)


if __name__ == "__main__":
    main()
