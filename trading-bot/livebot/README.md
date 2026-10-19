# NQ portfolio live bot (OANDA, NAS100 CFD) — GapFB + Pre-Fade + Opex

Rules: `../STRATEGY_NQ.md` §1. Logic: `strategy.py` (broker-independent), broker: `broker_oanda.py`, scheduler: `bot.py`.
Replay check vs the research (`test_replay.py`): 256 / 265 days identical (2025-01 → 2026-10); the 9 differences are days after
market half-days / holidays, where the research data skipped the half-day session and the bot (correctly) uses it.

What it does each weekday (New York time):
- 09:00 Pre-Open Fade (market + SL/TP, closed 13:00) · 09:30 Opex short on the 3rd Friday (market + SL/TP)
- 09:45 GapFB: one resting STOP entry valid to 10:30, 2×ATR stop + 5×ATR trailing stop attached on fill
- 15:55 close everything · 16:05 `journal.csv` + daily summary. Size = balance × risk_pct / stop for every trade.
- Telegram (optional): every signal, order, close and the daily P&L on your phone.
Replay checks: GapFB 256/265 days identical to the research; Pre-Fade 21/21 research days (+1 borderline); opex dates correct.

## Setup (only the steps that need you)
1. OANDA: open a **demo (practice)** account → Manage API Access → generate a token; note the account id (101-…).
2. Oracle Cloud: create a free account → Compute → Create instance (Ubuntu, "Always Free" shape) → download the SSH key →
   open **Cloud Shell** or SSH in.
3. On the VM paste:
   `bash <(curl -fsSL https://raw.githubusercontent.com/rotemGgGgGg/bigbrands/claude/serene-fermi-4483ji/trading-bot/livebot/deploy/install.sh)`
4. `nano ~/bigbrands/trading-bot/livebot/config.json` → paste token + account id (never share them in chat).
   Optional Telegram: talk to @BotFather → /newbot → paste the bot token; send your bot a message, open
   `https://api.telegram.org/bot<TOKEN>/getUpdates` and copy `chat.id`.
5. `cd ~/bigbrands/trading-bot/livebot && .venv/bin/python bot.py --check` → must print the balance.
6. `sudo systemctl enable --now gapfb` → the bot runs 24/7 and restarts itself. Logs: `journalctl -u gapfb -f`.
Live money later: change `"environment": "live"` and the live account id/token, then `sudo systemctl restart gapfb`.

## The website / phone app (same look as the .exe, + 16-year Performance page)
Same server, free HTTPS (needed for "Add to Home Screen"):
1. duckdns.org → log in → create a name (e.g. `rotem-nq`) → copy the token.
2. Oracle Cloud → your instance → Subnet → Security List → Add Ingress Rules: source `0.0.0.0/0`, TCP, ports `80` and `443`.
3. On the server: `bash ~/bigbrands/trading-bot/livebot/deploy/web_install.sh rotem-nq.duckdns.org <TOKEN>`
4. Phone: open `https://rotem-nq.duckdns.org` → Sign up (the first account is the owner; sign-up then closes) →
   iPhone: Share → Add to Home Screen · Android: ⋮ → Install app. Performance page: chart with 1M/3M/YTD/1Y/2Y/5Y/ALL,
   per-strategy, risk % and account size.
