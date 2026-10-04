"""Desktop chat window for talking to an existing Telegram bot.

Logs in as your own Telegram account (Telethon / MTProto), so the bot sees
the messages as coming from you. Keeps everything next to the .exe:
config.json and the login session file.
"""

import asyncio
import json
import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog

from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError

BG = "#17212b"
PANEL = "#0e1621"
ME = "#5ea0e8"
BOT = "#e6e6e6"
MUTED = "#7f8b96"
BUTTON = "#6ab3f3"


def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


CONFIG_PATH = os.path.join(app_dir(), "config.json")
SESSION_PATH = os.path.join(app_dir(), "telegram")  # Telethon adds .session
DEFAULT_BOT = "@agronn2bot"


def load_config(root):
    config = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, encoding="utf-8") as f:
            config = json.load(f)

    config.setdefault("bot_username", DEFAULT_BOT)
    questions = [
        ("api_id", "api_id from my.telegram.org -> API development tools:"),
        ("api_hash", "api_hash from my.telegram.org:"),
        ("bot_username", "Bot username (for example @some_bot):"),
    ]
    changed = False
    for key, prompt in questions:
        if not str(config.get(key, "")).strip():
            value = simpledialog.askstring("Setup", prompt, parent=root)
            if not value:
                sys.exit(0)
            config[key] = value.strip()
            changed = True
    if changed:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    return config


class TelegramWorker:
    """Runs Telethon on its own asyncio loop in a background thread.

    Talks to the GUI only through `ui_queue`, so tkinter is touched from the
    main thread alone.
    """

    def __init__(self, config, ui_queue):
        self.config = config
        self.ui = ui_queue
        self.loop = asyncio.new_event_loop()
        self.client = None
        self.bot = None
        self.messages = {}  # message id -> telethon Message (for button clicks)

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._main())
        except Exception as e:
            self.ui.put(("fatal", str(e)))

    def ask(self, prompt, secret=False):
        done = threading.Event()
        box = {}
        self.ui.put(("ask", prompt, secret, box, done))
        done.wait()
        return box.get("value")

    async def _login(self):
        await self.client.connect()
        if await self.client.is_user_authorized():
            return
        phone = await self.loop.run_in_executor(
            None, self.ask, "Your phone number with country code (e.g. +972501234567):"
        )
        if not phone:
            raise RuntimeError("Login cancelled")
        await self.client.send_code_request(phone)
        code = await self.loop.run_in_executor(
            None, self.ask, "Login code Telegram just sent you:"
        )
        try:
            await self.client.sign_in(phone, code)
        except SessionPasswordNeededError:
            password = await self.loop.run_in_executor(
                None, self.ask, "Two-step verification password:", True
            )
            await self.client.sign_in(password=password)

    async def _main(self):
        self.client = TelegramClient(
            SESSION_PATH, int(self.config["api_id"]), self.config["api_hash"]
        )
        self.ui.put(("status", "Connecting..."))
        await self._login()

        self.bot = await self.client.get_entity(self.config["bot_username"])
        name = getattr(self.bot, "first_name", None) or self.config["bot_username"]
        self.ui.put(("title", name))

        history = await self.client.get_messages(self.bot, limit=30)
        for msg in reversed(history):
            self._show(msg)

        @self.client.on(events.NewMessage(chats=self.bot))
        async def on_new(event):
            self._show(event.message)

        @self.client.on(events.MessageEdited(chats=self.bot))
        async def on_edit(event):
            self._show(event.message, edited=True)

        self.ui.put(("status", "Connected"))
        await self.client.run_until_disconnected()

    def _show(self, msg, edited=False):
        self.messages[msg.id] = msg
        text = msg.message or ""
        if msg.media and not text:
            text = "[media]"
        elif msg.media:
            text = "[media] " + text
        buttons = [[b.text for b in row] for row in (msg.buttons or [])]
        self.ui.put(("message", msg.id, msg.out, text, buttons, edited))

    def send(self, text):
        asyncio.run_coroutine_threadsafe(
            self.client.send_message(self.bot, text), self.loop
        )

    def click(self, msg_id, row, col):
        msg = self.messages.get(msg_id)
        if msg:
            asyncio.run_coroutine_threadsafe(msg.click(row, col), self.loop)


class ChatWindow:
    def __init__(self, root):
        self.root = root
        root.title("Telegram Bot Chat")
        root.geometry("520x680")
        root.configure(bg=BG)

        self.header = tk.Label(
            root, text="...", bg=PANEL, fg="white", font=("Segoe UI", 13, "bold"), pady=10
        )
        self.header.pack(fill="x")
        self.status = tk.Label(root, text="", bg=PANEL, fg=MUTED, font=("Segoe UI", 9))
        self.status.pack(fill="x")

        frame = tk.Frame(root, bg=BG)
        frame.pack(fill="both", expand=True)
        scroll = tk.Scrollbar(frame)
        scroll.pack(side="right", fill="y")
        self.chat = tk.Text(
            frame, bg=BG, fg=BOT, wrap="word", font=("Segoe UI", 11), bd=0,
            padx=12, pady=8, state="disabled", yscrollcommand=scroll.set, cursor="arrow",
        )
        self.chat.pack(fill="both", expand=True)
        scroll.config(command=self.chat.yview)
        self.chat.tag_config("me", foreground=ME, justify="right", spacing3=10)
        self.chat.tag_config("bot", foreground=BOT, justify="left", spacing3=10)
        self.chat.tag_config("button", foreground=BUTTON, underline=True)

        bottom = tk.Frame(root, bg=PANEL, pady=8, padx=8)
        bottom.pack(fill="x")
        self.entry = tk.Entry(
            bottom, bg="#242f3d", fg="white", insertbackground="white",
            font=("Segoe UI", 11), bd=0, relief="flat",
        )
        self.entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 8))
        self.entry.bind("<Return>", lambda e: self.on_send())
        tk.Button(
            bottom, text="Send", command=self.on_send, bg="#2b5278", fg="white",
            bd=0, padx=16, activebackground="#3a6a99", activeforeground="white",
        ).pack(side="right", ipady=4)
        self.entry.focus()

        self.queue = queue.Queue()
        self.worker = TelegramWorker(load_config(root), self.queue)
        self.worker.start()
        self.poll()

    def on_send(self):
        text = self.entry.get().strip()
        if text:
            self.entry.delete(0, "end")
            self.worker.send(text)

    def render(self, msg_id, out, text, buttons, edited):
        mark = f"msg{msg_id}"
        self.chat.config(state="normal")
        existing = self.chat.tag_ranges(mark)
        if existing:
            self.chat.delete(existing[0], existing[1])
            index = existing[0]
        elif edited:
            self.chat.config(state="disabled")
            return  # edit of a message older than the loaded history
        else:
            index = "end"

        # A right-gravity mark moves forward with each insert, so chunks land in order.
        self.chat.mark_set("cursor_pt", "end-1c" if index == "end" else index)
        self.chat.mark_gravity("cursor_pt", "right")

        def put(chunk, tags):
            self.chat.insert("cursor_pt", chunk, tags)

        put(text + "\n", ("me" if out else "bot", mark))
        for r, row in enumerate(buttons):
            for c, label in enumerate(row):
                tag = f"btn{msg_id}_{r}_{c}"
                put(f"[{label}]", ("button", tag, mark))
                put("  ", (mark,))
                self.chat.tag_bind(
                    tag, "<Button-1>",
                    lambda e, m=msg_id, rr=r, cc=c: self.worker.click(m, rr, cc),
                )
            put("\n", (mark,))
        self.chat.config(state="disabled")
        if index == "end":
            self.chat.see("end")

    def poll(self):
        while not self.queue.empty():
            item = self.queue.get()
            kind = item[0]
            if kind == "message":
                self.render(*item[1:])
            elif kind == "status":
                self.status.config(text=item[1])
            elif kind == "title":
                self.header.config(text=item[1])
            elif kind == "ask":
                _, prompt, secret, box, done = item
                box["value"] = simpledialog.askstring(
                    "Telegram login", prompt, parent=self.root, show="*" if secret else None
                )
                done.set()
            elif kind == "fatal":
                messagebox.showerror("Error", item[1])
                self.root.destroy()
                return
        self.root.after(100, self.poll)


def main():
    root = tk.Tk()
    ChatWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
