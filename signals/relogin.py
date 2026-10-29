"""Switches the bot to another Telegram account, run by that account's owner.

Logs in with a phone number and the code Telegram sends to it, then writes
the new session straight into the .env beside this file, so the credential
is never printed. It also lists the channels that account can read and, when
one matches the name given, points the bot at it by its ID.

    python relogin.py "Essamtrades VIP"

The old session stays valid until it is removed in Telegram under
Settings > Devices on the account it belonged to.
"""
import re
import sys
from pathlib import Path

try:
    from telethon.sync import TelegramClient
    from telethon.sessions import StringSession
except ImportError:
    raise SystemExit("pip install telethon")

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ENV = Path(__file__).with_name(".env")


def norm(t: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", t or "").lower().split())


def set_keys(values: dict) -> None:
    lines = ENV.read_text(encoding="utf-8-sig").splitlines()
    seen = set()
    for i, line in enumerate(lines):
        k = line.split("=", 1)[0].strip()
        if k in values:
            lines[i] = f"{k}={values[k]}"
            seen.add(k)
    lines += [f"{k}={v}" for k, v in values.items() if k not in seen]
    ENV.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    if not ENV.exists():
        raise SystemExit(f"no .env next to this file ({ENV})")
    env = {}
    for line in ENV.read_text(encoding="utf-8-sig").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    want = norm(" ".join(sys.argv[1:]))

    print("Telegram will ask for the phone number of the account that has the channel,")
    print("then for the code it sends to that account (and the 2FA password if there is one).\n")
    with TelegramClient(StringSession(), int(env["TG_API_ID"]), env["TG_API_HASH"]) as client:
        me = client.get_me()
        print(f"\nlogged in as {me.first_name} (@{me.username})\n")
        dialogs = [d for d in client.iter_dialogs() if d.is_channel or d.is_group]
        print("channels and groups on this account:")
        for d in dialogs:
            print(f"  {d.id:>16}   {d.name}")
        values = {"TG_SESSION": client.session.save()}
        if want:
            found = [d for d in dialogs if norm(d.name) == want] or \
                    [d for d in dialogs if want in norm(d.name)]
            if len(found) == 1:
                values["TG_SOURCE"] = str(found[0].id)
                print(f"\nthe bot will read: {found[0].name} (id {found[0].id})")
            else:
                print(f"\n{len(found)} channels match {want!r}; TG_SOURCE left as it was")
        set_keys(values)
        print("\nsaved to .env. Start the bot again.")


if __name__ == "__main__":
    main()
