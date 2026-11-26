# Prompt for Lovable — Edge Lab

Paste everything below the line into a new Lovable project. Attach (or sync via GitHub) the files listed under "Files".

---

Build **Edge Lab**, my personal quant-research workspace for trading strategies (NQ futures and JPY crosses). It is a
real tool, not a marketing site: every number comes from the data files I give you, never from placeholders.

## Files (use them as-is)
From `edge-lab-static.zip`:
- `data/data.json` — strategy registry: id, name, market, status LIVE/WATCH/DEAD, family, rule, entry, exit, params,
  random-twin p, notes, Monte Carlo summary (`mc`), the SP-model deep dive (`sp`), the "book", theories tested.
- `data/trades.json` — every trade per strategy: `{ [id]: { units, t: ISO date[], r: R per trade[] } }`.
- `data/history.json` — research commits `{ id, at, type: "commit", title }`.
- `js/engine/stats.mjs`, `enrich.mjs`, `montecarlo.mjs`, `portfolio.mjs` — the maths. Port them to TypeScript
  **without changing any formula** (enrich = metrics per strategy, montecarlo = bootstrap with capital, risk %, fixed or
  compounding sizing, ruin threshold, seed; portfolio = daily grid, Sharpe, correlation, risk contribution, monthly
  histogram, portfolio Monte Carlo).
- `js/learn/content.js` — the Hebrew step-by-step lessons (RTL). Mount it as-is on the Learn page
  (`mountLearn(element, normalise(strategies))`), or port it keeping every step, question and calculator.
- `js/api-static.js` — reference for how each page gets its data in the browser.

## Pages
1. **Welcome** — "Hello, Mr. Rotem." / "Your research environment is ready." Large chat input ("Ask anything about your
   strategies…"), suggestion chips (Analyze my latest strategy · Compare all NQ strategies · Run a Monte Carlo simulation ·
   Find the best performing entry conditions · Test a volatility filter · Investigate drawdown behavior), link "Open workspace".
2. **Overview** — counts (tested / live / watching / rejected / theories screened), best out-of-sample strategy with
   its equity curve, live strategies with sparklines, recent experiments, latest activity, the book, the 4 research gates.
3. **Strategies** — sortable, searchable table (status filter, compare up to 4 with an overlaid equity chart).
   Strategy page: rules (description, entry, exit, parameters, notes), KPIs, equity + drawdown, R by year,
   trade statistics, one-year Monte Carlo. For `sp` and `sp_B` also the SP breakdown from `data.sp`.
4. **Monte Carlo** — controls (strategy, simulations 1k/5k/10k/20k, horizon 1/2/5 years, capital, risk per R,
   fixed/compounding, ruin %, seed) and a large fan chart: 5–95% and 25–75% bands in soft greys, white median, dashed
   p5/p95, muted-red ruin line, ending-distribution histogram on the right, hover tooltip. KPIs: P(positive), median,
   5th, 95th, drawdown p95, risk of ruin.
5. **Portfolio Lab** — weight sliders per strategy, presets (Gotobi + RDM, All live, Equal), combined equity + drawdown,
   correlation heatmap, risk contribution, monthly histogram, portfolio Monte Carlo.
6. **Experiments** — lifecycle Draft → Running → Completed → Reviewed → Accepted / Rejected, created from a base strategy,
   side-by-side diff of changed rules, notes, timeline; saved in the browser (localStorage) unless the agent is connected.
7. **Research History** — timeline of commits and app events, search and type filter.
8. **Graveyard** — every DEAD strategy with its rule, the reason it died, 2020–26 result and p.
9. **Learn** — the lessons from `content.js`.
10. **Settings → Agent** — field "Local Edge Lab address" (default `http://localhost:3007`) and "Pairing code",
    a Test button, and the agent status.

## The research agent (runs on my computer, on my Claude subscription — never an API key in this app)
The agent is NOT run by Lovable. My computer runs the Edge Lab server (Claude Code signed in with my subscription).
This app talks to it over HTTP:
- Base URL = the address from Settings. Every request sends `Authorization: Bearer <pairing code>`.
- `GET /api/health` → `{ agent: { available, version, error }, settings, permissions, models }`
- `POST /api/chat { message, conversationId?, context? }` → `{ conversationId, jobId, userMsg, assistantMsg }`
- `GET /api/jobs/{jobId}/stream?token=<pairing code>` → Server-Sent Events. Event `data` JSON `type`:
  `phase {label}`, `delta {text}`, `tool {id, summary, command, phase}`, `tool_result {id, ok}`, `error {message}`,
  `result {ok, costUsd, durationMs, denied}`, `cancelled`, `end`.
- `POST /api/jobs/{jobId}/cancel`, `GET /api/conversations`, `GET /api/conversations/{id}`
- `GET/POST/PATCH /api/experiments…`, `POST /api/experiments/{id}/run` (same shapes as the local app).
When the agent is not reachable, show a calm notice ("Your computer is offline — start Edge Lab on it") and keep every
other page working from the data files. Show the streaming answer with markdown, a collapsible list of tool steps with
status, a phase line ("Reading files", "Running research", "Writing"), and a Stop button.
The chat lives on the Welcome screen, on a full Research page, and as a slide-over panel from a floating bottom bar on
every page (⌘K focuses it).

## Design
Dark, calm, premium — Linear / Vercel level. Not a trading terminal.
- Colours: background #050505, #0A0A0A; cards #101010, raised #151515; borders #222222; text #F5F5F5, secondary #888888,
  muted #555555; accent #E74747, deep accent #A92E35; positive #D9D9D9; negative #E74747. Red only for focus, risk and
  the agent.
- Type: Geist (UI), Geist Mono (every number). Small refined labels, generous spacing, thin borders, few cards.
- Slim collapsible sidebar (Lucide icons): New Research, Overview, Strategies, Experiments, Portfolio Lab, Monte Carlo,
  Research History, Graveyard, Learn, Settings; footer with agent status and "Rotem".
- Motion (original, tasteful, respects prefers-reduced-motion):
  · Opening: a soft blurred red light orb that breathes slowly, greeting fades up with a slight blur-to-sharp, then the
    chat input rises in.
  · Large numbers (theories screened, Sharpe, trades) count up when they enter the viewport, in a subtle metallic
    white-to-grey gradient.
  · Sections reveal on scroll (fade + 8px rise, staggered). Charts draw their lines in.
  · A slow horizontal ticker of our own strategies (name · status · 2020–26 R), not logos.
- Fully responsive (sidebar becomes a drawer on phones).

## Do not
- Do not use any other company's name, logo, screenshots, testimonials, statistics or copy (in particular nothing
  from LiquidJournal or any prop-firm / broker logos). Everything on screen is Edge Lab and my own data.
- Do not invent numbers, users, reviews or results. Do not add pricing, sign-up or affiliate sections.
- Do not call any AI API from this app or ask for an API key.
