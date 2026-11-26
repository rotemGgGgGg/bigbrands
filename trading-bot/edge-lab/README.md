# Edge Lab — quant research workspace

A local web app for the NQ / JPY strategy research in `trading-bot/research`: strategy explorer, Monte Carlo lab,
portfolio lab, experiment lifecycle, research history, graveyard, and a research agent that runs **Claude Code** inside
the research folder.

```bash
cd trading-bot/edge-lab
npm start            # → http://localhost:3007   (PORT=3008 npm start if 3007 is taken)
npm test             # engine tests (Monte Carlo, metrics, portfolio)
```
Needs Node 20.12+. No dependencies to install. The agent needs the Claude Code CLI on the same machine, signed in
(`claude`, then `/login`). Settings go in an optional `.env` file next to this README (copy `.env.example`; gitignored).

### Windows (PowerShell 5 has no `&&`: one command per line)
```powershell
cd C:\Users\User\bigbrands
git pull
cd trading-bot\edge-lab
npm start
```
The server finds `claude.cmd` by itself and calls Python as `python`. Keep the window open while you use the app.

## Billing: subscription or API key
- **Claude subscription** (default): the agent uses the account Claude Code is signed in with. Sign in with your
  Claude account (`claude` → `/login` → Claude account), not an API key. Any `ANTHROPIC_API_KEY` in the environment is
  removed for these runs, so nothing is billed per token by accident.
- **Claude API key**: put `EDGE_LAB_API_KEY=sk-ant-…` in `.env`, restart, then Settings → Billing → Claude API key.
  Each run gets `--max-budget-usd` (default $2, editable). The key is only read by the server and passed to the CLI;
  it never reaches the browser.

## Security model
- Default: listens on `127.0.0.1` only, no login — only your own computer can open it.
- `EDGE_LAB_PASSWORD` (12+ characters) turns on sign-in for every API call: HttpOnly + SameSite=Strict session cookie,
  30-day sessions, "sign out every device", 5 failed attempts per 15 minutes per address.
- The server refuses to listen on anything but localhost (`HOST=0.0.0.0`) without a password.
- Unknown `Host` headers are rejected (DNS rebinding); cross-origin writes are rejected; strict Content-Security-Policy,
  no framing, no referrer.
- The agent only gets the tools of the chosen permission level (`--permission-mode dontAsk`), works inside
  `trading-bot/research`, and has no web access.

## Bridge: a web front end (e.g. Lovable) using this computer's agent
Set `EDGE_LAB_BRIDGE_ORIGINS=https://your-app.lovable.app` in `.env` and restart. Only that origin may call the API,
and only with the pairing code (shown at startup and in Settings → Access; "New code" revokes the old one).
The agent still runs here, on your Claude Code sign-in; the web app never holds a key. Chrome's private-network
preflight is answered for the listed origins only. `LOVABLE_PROMPT.md` describes the front end and the API contract.

## Access from your phone (private, not public)
Do **not** put Edge Lab on a public address: the agent runs Python on your computer. Use Tailscale (free), which makes
a private network between your own devices:
1. Install Tailscale on the computer and the phone, sign in to the same account on both.
2. In `.env`: `EDGE_LAB_PASSWORD=…` and `ALLOWED_HOSTS=<your-pc>.<tailnet>.ts.net` (shown in the Tailscale app).
3. Start Edge Lab (`npm start`), then in another window: `tailscale serve --bg 3007`.
4. On the phone: `https://<your-pc>.<tailnet>.ts.net` → sign in with the password.
If a page says `Host "…" is not allowed`, put exactly that name in `ALLOWED_HOSTS` and restart.

## Phase 1 — audit of the previous Edge Lab (research/lab)
| Piece | Where | What it held |
|---|---|---|
| Registry | `research/lab/build.py` → `data.json` | 17 strategies: id, name, market, status LIVE/WATCH/DEAD, family, rule, target R:R, random-twin p, note; book figures; theories screened; SP deep-dive (`sp.json`) |
| Series | `series.json` (inline script) | per strategy: trades/yr, win %, avg R, 2012–19 / 2020–26 avg and t, R by year, positive years, downsampled curve, Monte Carlo (5,000 one-year bootstrap paths: P(year>0), median, 5th pct, 95th pct drawdown, fan) |
| Page | `research/lab/index.html` | KPI strip, leaderboard + inspector (equity, MC fan, yearly bars), SP Model section (two London windows, by scenario/side/hour, fix attempts), book, graveyard, method (4 gates) |

What changed for the app:
- `research/lab/export_trades.py` now stores **every trade** (`trades.json`, 19,136 trades, same sources as `series.json`), so all
  metrics, drawdowns, Monte Carlo and portfolio maths are recomputed from real trades instead of stored summaries.
- `build.py` gained entry / exit / parameters for the strategies with trade data, and the SP London 02:00 variant as its own row.
- Units are kept as they were: Gotobi and RDM in normalised R (1 = average 2012–19 trade), the others in R after costs, SP before costs.

## Architecture
```
public/            vanilla ES modules, no build step
  js/views/*       welcome, research, overview, strategies (+ inspector, compare, SP breakdown), montecarlo, portfolio,
                   experiments, history, graveyard, settings
  js/charts.js     SVG charts: equity/drawdown, Monte Carlo fan + ending distribution, bars, histogram, heatmap
  js/chat.js       chatbar, streaming conversation thread (used by welcome, research page, side panel)
server/server.mjs  HTTP API + SSE on 127.0.0.1 only
  lib/data.mjs       registry + trades → metrics (expectancy, t, IS/OOS, max DD, streaks, years, curves)
  lib/montecarlo.mjs i.i.d. bootstrap: sims, horizon, capital, risk %, fixed/compounding, ruin threshold, seed
  lib/portfolio.mjs  daily grid → combined curve, drawdown, Sharpe, correlation, risk contribution, monthly histogram, MC
  lib/agent.mjs      Claude Code bridge (below)
  lib/store.mjs      JSON files in edge-lab/store/ (conversations, experiments, events, settings) — gitignored
```

## The research agent
The browser never runs commands. It sends a message; the server starts
`claude -p --output-format stream-json --verbose --include-partial-messages --permission-mode dontAsk --allowedTools …`
with `cwd = trading-bot/research`, streams the events to the page over SSE, and saves the conversation.
- **Permission levels** (Settings): *Read only* (Read, Glob, Grep) · *Analyze* (+ `python3 …`, `ls`, read-only git) ·
  *Build* (+ Edit, Write). `dontAsk` refuses anything outside the list; refused tools are shown under the answer.
- Conversations resume the same Claude Code session (`--resume`). Runs can be cancelled; one run per conversation.
- The agent gets a short brief of the research rules (choose on 2012–19, judge 2020–26 once, costs, random twin, no invented
  numbers) and ends test reports with a JSON metrics block, which the Experiment Lab parses for comparisons.
- No keys pass through the app: the CLI uses your own Claude Code sign-in. The server binds to 127.0.0.1 and rejects
  requests from other origins and hosts (CSRF / DNS-rebinding guard).

## Experiments
Draft → Running → Completed → Reviewed → Accepted / Rejected. A variation snapshots its base strategy's rules, so the
diff of every changed field is kept; the base strategy files are never touched. "Run with agent" sends the experiment
to Claude Code with the research gates; the result and its metrics are saved back on the experiment.

## Known limits
- Monte Carlo draws trades independently: streaks and regime changes are not preserved.
- Strategies rejected from summary statistics only (CRT, macro events, …) have no trade series, so they show a verdict, not charts.
- The "book" numbers on Overview come from the original research run; the Portfolio Lab recomputes its own from trades.
