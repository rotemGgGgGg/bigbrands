# Edge Lab — quant research workspace

A local web app for the NQ / JPY strategy research in `trading-bot/research`: strategy explorer, Monte Carlo lab,
portfolio lab, experiment lifecycle, research history, graveyard, and a research agent that runs **Claude Code** inside
the research folder.

```bash
cd trading-bot/edge-lab
npm start            # → http://localhost:3007   (PORT=3008 npm start if 3007 is taken)
npm test             # engine tests (Monte Carlo, metrics, portfolio)
```
Needs Node 20+. No dependencies to install. The agent needs the Claude Code CLI on the same machine, signed in
(`claude` once in a terminal). If it lives elsewhere: `CLAUDE_BIN=/path/to/claude npm start`.

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
