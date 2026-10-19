# NQ Portfolio EA (MetaTrader 5) — GapFB + Pre-Open Fade + Opex short

Same rules as `../STRATEGY_NQ.md` and the Python bot (`../livebot`). Times are computed in New York time from GMT, so the
broker's server time zone does not matter.

## Install (demo first)
1. Open a **demo** MT5 account at a regulated broker that accepts you (e.g. Pepperstone or FP Markets — confirm Israel at sign-up).
2. MT5 → File → Open Data Folder → `MQL5/Experts` → copy `NQ_Portfolio_EA.mq5` there.
3. MT5 → Navigator → right-click Expert Advisors → Refresh. Double-click the EA in MetaEditor → **Compile** (F7) — send me any error.
4. Open ONE chart of the Nasdaq-100 CFD (NAS100 / US100 / USTEC), drag the EA on it, tick "Allow Algo Trading", set RiskPct (1).
5. Toolbar → **Algo Trading** ON (green). The Experts tab prints "NQ Portfolio EA started … NY time now …" — check that NY time is right.
6. Optional Telegram: Tools → Options → Expert Advisors → allow WebRequest for `https://api.telegram.org`, fill TelegramToken / TelegramChatId.

## Running 24/7
- MetaQuotes VPS: right-click the account in Navigator → "Register a Virtual Server" (~$10–15/month), then migrate the chart+EA.
- Or any Windows VPS. (Linux + Wine works but is fragile.)

## Schedule (NY time, weekdays)
09:00 Pre-Fade market order (SL 1.0× move, TP 0.5× move), closed 13:00 · 09:30 Opex short on the 3rd Friday (SL 0.4σ, TP 0.8σ)
· 09:45 GapFB stop order valid to 10:30, SL 2×ATR, trailing 5×ATR · 15:55 everything closed.
Magic numbers: 880101 GapFB, 880102 Pre-Fade, 880103 Opex.
