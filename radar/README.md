# Radar — tracked-wallet confluence

Alerts when **several independent tracked wallets buy the same Solana token
within a short window**. A single tracked wallet buying something is what the
wallet-tracker app already spams; the signal is convergence.

No trading, no orders. It only says: *look at this now*.

## What it does

```
593 tracked wallets
   -> poll each wallet's new transactions (Solana RPC)
   -> keep only buys (token balance up AND SOL net spent)
   -> group buys by mint inside a 10-minute window
   -> >= 3 distinct wallets on one mint  = event
   -> score 0-100 (breadth / speed / size / novelty)
   -> Telegram alert, deduped per mint
   -> every alert stored in SQLite for later calibration
```

X/Twitter is deliberately **not** part of this stage. The wallet layer stands
on its own and costs nothing; social costs money and only makes sense once the
wallet layer proves it produces alerts worth reading.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env      # fill in HELIUS_API_KEY (free tier is enough)
python main.py --dry-run  # prints alerts to the terminal
```

Add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` to `.env` and drop `--dry-run`
to get alerts on your phone.

Flags: `--bootstrap-only` (record starting cursors and exit), `--once` (one
pass over all wallets), `--dry-run` (never touch Telegram).

## Scoring

| Component | Weight | Meaning |
|---|---|---|
| breadth | 40% | how many distinct wallets converged |
| speed | 25% | how tightly packed in time |
| size | 15% | total SOL committed |
| novelty | 20% | how early we are on this mint |

Price change is not an input on purpose. The question is *what is happening*,
not *how much has it already moved*.

## Tuning

All knobs live in `.env` (see `.env.example`). The ones that matter:

- `MIN_WALLETS` — raise to 4 for fewer, stronger alerts.
- `MIN_SCORE_TO_ALERT` — raise to cut volume without changing the rule.
- `MIN_SOL_BUY` — ignores dust; raise it if you see noise from tiny buys.
- `SKIP_STALE_DAYS` — wallets idle longer than this are skipped in the scan.

## Notes on the wallet list

`data/wallets.json` is a wallet-tracker export (593 addresses). A bootstrap run
reports last-activity per wallet; as of the first run, 247 had traded in the
last day, 297 within a week, and 209 had been idle for over a month. The idle
ones are skipped automatically so they do not burn RPC calls.

## Calibration

Every alert is written to the `alerts` table in `radar.db`. After a week of
running, compare alerts against what actually happened and adjust
`MIN_WALLETS` / `MIN_SCORE_TO_ALERT`. Without that loop the thresholds are
guesses.
