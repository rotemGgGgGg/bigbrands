"""One-time Telegram login, run by the account's owner.

Telethon needs a real login the first time: a phone number, then a code
Telegram sends to that account. That code grants full access to the account,
which is why this is a script the owner runs rather than something handed
over in a chat. What it prints at the end is a session string — still
sensitive, but revocable from Telegram's own Settings → Devices, and it
cannot be used to request a new code.

    pip install telethon
    python3 signals/login.py

Then put the printed line into signals/.env as TG_SESSION.
"""
import os

try:
    from telethon.sync import TelegramClient
    from telethon.sessions import StringSession
except ImportError:
    raise SystemExit("pip install telethon")


def read_env(path: str = "signals/.env") -> dict:
    out = {}
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    return out


def main() -> None:
    env = read_env()
    api_id = env.get("TG_API_ID")
    api_hash = env.get("TG_API_HASH")
    if not api_id or not api_hash:
        raise SystemExit("set TG_API_ID and TG_API_HASH in signals/.env first")

    with TelegramClient(StringSession(), int(api_id), api_hash) as client:
        me = client.get_me()
        print(f"\nlogged in as {me.first_name} (@{me.username})\n")
        print("Add this line to signals/.env — it is a credential, keep it out of git:\n")
        print(f"TG_SESSION={client.session.save()}\n")
        print("Channels and groups this account can read:\n")
        for dialog in client.iter_dialogs():
            if dialog.is_channel or dialog.is_group:
                print(f"  {dialog.id:>16}   {dialog.name}")
        print("\nPut the one you want into signals/.env as TG_SOURCE.")


if __name__ == "__main__":
    main()
