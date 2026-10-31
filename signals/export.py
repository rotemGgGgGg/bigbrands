"""Copies the channel's past messages to the desk, so their formats can be
studied without Telegram access. Run it on the machine where the bot runs,
with the bot stopped: one Telegram session should not be used by two
programs at once.

    python export.py            # the last 1500 messages
    python export.py 4000       # more

Each line is: date, message id, the id it replies to (if any), the text.
A copy is also written to vip_history.txt beside this file.
"""
import json
import re
import sys
import urllib.request
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

HERE = Path(__file__).parent
ENV = {}
for line in (HERE / ".env").read_text(encoding="utf-8-sig").splitlines():
    if "=" in line and not line.lstrip().startswith("#"):
        k, v = line.split("=", 1)
        ENV[k.strip()] = v.strip()


def post(payload: dict) -> None:
    req = urllib.request.Request(
        ENV["DESK_URL"].rstrip("/") + "/api/history", data=json.dumps(payload).encode(),
        headers={"authorization": f"Bearer {ENV['DESK_INGEST_KEY']}",
                 "content-type": "application/json", "user-agent": "tape-bot/1.0"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        r.read()


def main() -> None:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 1500
    source = ENV.get("TG_SOURCE", "")
    target = int(source) if source.lstrip("-").isdigit() else source
    lines = []
    with TelegramClient(StringSession(ENV["TG_SESSION"]), int(ENV["TG_API_ID"]), ENV["TG_API_HASH"]) as client:
        for m in client.iter_messages(target, limit=limit):
            text = (m.raw_text or "").strip()
            kind = "photo " if m.photo else "file " if m.document else ""
            if not text and not kind:
                continue
            reply = getattr(m, "reply_to_msg_id", None)
            lines.append(f"[{m.date:%Y-%m-%d %H:%M}] #{m.id}" + (f" reply-to #{reply}" if reply else "")
                         + f" {kind}| " + re.sub(r"\s*\n\s*", " / ", text))
    lines.reverse()
    text = "\n".join(lines)
    (HERE / "vip_history.txt").write_text(text, encoding="utf-8")
    chunks = [text[i:i + 300000] for i in range(0, len(text), 300000)] or [""]
    for i, chunk in enumerate(chunks):
        post({"part": i, "parts": len(chunks), "text": chunk})
    print(f"{len(lines)} messages sent to the desk in {len(chunks)} part(s), and saved to vip_history.txt")


if __name__ == "__main__":
    main()
