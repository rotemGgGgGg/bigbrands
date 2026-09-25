# Signal Scanner: Data Feasibility Research (Phase 0)

Status: **research only. No scoring engine or UI has been built yet.** This file is here for review before any build work starts.
Date: 2026-09-25. Everything marked "tested" was run against live endpoints from this environment.

---

## TL;DR: the uncomfortable parts first

1. **Insider cluster buying will be silent for almost all of this watchlist.** I pulled every Form 4 from the last 365 days for 8 AI-infrastructure names (POWL, PWR, VRT, HUBB, MU, GEV, ETN, NVT): **~470 Form 4s, 14 open-market purchase lines from only 5 people, 0 clusters.** Every buyer bought alone: Micron (3 buys, 1 person), Eaton (6 buys, 1 director over 10 months), nVent (1 person), and Hubbell (1 buy). Insiders in momentum sectors sell, and clusters tend to show up in beaten-down names. As specified, signal #1 would read 0 for about 95% of ticker-weeks.
2. **Foundry and memory names mostly can't be covered.** TSMC, ASML, and other foreign private issuers are exempt from Section 16, so they never file Form 4. Samsung and SK Hynix aren't SEC filers at all. Semis don't report a meaningful backlog either. For those tickers, only the analyst revision signal works.
3. **Backlog has no standard XBRL tag.** The closest standard tag is `RevenueRemainingPerformanceObligation` (RPO). RPO isn't backlog (it leaves out cancellable orders), and coverage is patchy (see table below).
4. **Analyst revision direction is the easiest signal to get, not the hardest.** Alpha Vantage's `EARNINGS_ESTIMATES` returns revision direction directly, on the free tier. This should be the backbone of the score.
5. **Cost: $0/month** at 15–30 tickers per week.

---

## 1. SEC EDGAR: Form 4 (insider transactions)

| Item | Finding | Confidence |
|---|---|---|
| Ticker → CIK | `https://www.sec.gov/files/company_tickers.json` (tested) | Certain |
| Filing list | `https://data.sec.gov/submissions/CIK##########.json`: `filings.recent` holds the latest ~1000 filings, with older pages under `filings.files` (tested) | Certain |
| Form 4 XML | `primaryDocument` looks like `xslF345X06/foo.xml`. That's the rendered HTML, so **strip the `xslF345X06/` prefix** to get raw XML at `/Archives/edgar/data/{cik}/{accession-no-dashes}/foo.xml` (tested) | Certain |
| Fields needed | `rptOwnerCik`, `isDirector/isOfficer/officerTitle`, `transactionCode` (`P` = open-market buy), `transactionShares`, `transactionPricePerShare`, `transactionDate`, `aff10b5One` (10b5-1 plan flag, schema X0609+; appears as `0`/`false`/`1`/`true`) | Certain |
| Rate limit | 10 requests/sec and a **declared User-Agent with a contact email is required**. SEC blocks anonymous UAs. | Certain |
| Weekly volume | ~20 tickers × (1 submissions call + ~1–5 new Form 4s) ≈ 50–120 requests/week | Likely |

**Cluster detection (feasible, straightforward):**
- Keep only `transactionCode == P` with `aff10b5One` false (planned trades carry no information) and value ≥ $25k (drops token buys).
- Cluster = **≥2 distinct `rptOwnerCik`** buying the same issuer within a rolling 30-day window.
- Store every parsed transaction in SQLite keyed by accession number, so each filing is parsed only once.

**Fallback for low signal density:** keep the signal but show it as a **binary event flag** ("Insider cluster: 3 insiders, $1.2M, 14 days") instead of a continuous component that is almost always 0. As a continuous 0, it would just dilute the composite score.

## 2. SEC EDGAR: Backlog / book-to-bill

Tested `companyfacts` (`https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json`) for every tag matching backlog / RPO / bookings, across all namespaces including company-custom tags:

| Ticker | RPO in XBRL? | Notes |
|---|---|---|
| GEV | Yes, quarterly | $176B at 2026-06-30. Usable |
| PWR | Yes, quarterly | $33.6B. Usable |
| POWL | Yes, quarterly | **Rounded to $0.1B**, so QoQ deltas are coarse |
| MU | Sporadic (6 facts, gap 2021→2026) | Not usable |
| HUBB | Stopped in 2020 | Not usable |
| VRT | **None** | Backlog and book-to-bill appear only in 8-K earnings release text |

Confidence: **Certain** for these six companies. **Likely** that the pattern holds more broadly: industrial project businesses tag RPO, while product businesses often don't.

**Text fallback (tested, works but is brittle):** EDGAR full-text search `https://efts.sec.gov/LATEST/search-index?q="book-to-bill"&ciks=...&forms=8-K&startdt=...&enddt=...` found Vertiv's EX-99.1 earnings releases. The text says *"book-to-bill ratio was ~2.9x and backlog increased to $15.0B"*, which a regex can extract. But Vertiv used that phrasing in only 3 of ~5 releases in the window, and each company words it differently.

**Recommended approach (tiered):**
1. XBRL RPO where it exists → automated. Implied book-to-bill ≈ `1 + ΔRPO_qoq / Revenue_q` (revenue from `RevenueFromContractWithCustomerExcludingAssessedTax`).
2. Otherwise, regex the latest 8-K EX-99.1 / 10-Q for backlog and book-to-bill → show it as a **"candidate value, confirm?"** in the UI, one tap to accept. A human confirming 5–10 numbers per quarter is cheaper and more reliable than a fragile parser.
3. Otherwise, "N/A" for this ticker. That's expected for semis and memory.

This signal changes **once per quarter**, so the weekly scan will mostly show "unchanged, last updated N weeks ago". The UI has to show that staleness honestly.

## 3. Analyst estimate revisions: provider comparison

| Provider | Revision direction exposed? | Free tier | Verdict |
|---|---|---|---|
| **Alpha Vantage** `EARNINGS_ESTIMATES` | **Yes.** Per fiscal quarter and year: `eps_estimate_average` plus `_7/_30/_60/_90_days_ago`, `revision_up/down_trailing_7/30_days`, `analyst_count`, plus revenue estimates (tested with demo key on IBM) | 25 requests/day. The endpoint is not marked Premium in the docs, but I couldn't confirm that with a real free key. | **Use this** (Likely it's free) |
| Financial Modeling Prep `analyst-estimates` | Current consensus per fiscal period only. No snapshots and no up/down counts, so you'd have to build history by snapshotting weekly. | 250 calls/day, some data partial on free tier | Backup only (Likely) |
| Finnhub `eps-estimate` / `revenue-estimate` / `upgrade-downgrade` | Estimates exist, but these endpoints return **403 on the free tier** (premium only, per multiple independent reports) | n/a | Rejected (Likely) |

Alpha Vantage limits and gaps:
- It can't backfill beyond the 90-day-ago snapshot, so each ticker starts with a 5-point history (now, 7, 30, 60, 90 days ago). Weekly snapshots stored in SQLite build real history from then on.
- If `EARNINGS_ESTIMATES` turns out to be premium-gated for a real free key, the fallback is FMP plus our own weekly snapshots. That works, but it needs ~4 weeks before the first revision direction is meaningful.

## 4. Cost at personal scale

| Source | Weekly calls (20 tickers) | Free limit | Cost |
|---|---|---|---|
| SEC EDGAR | ~50–120 | 10/sec, no daily cap | $0 |
| Alpha Vantage | 20 (1 per ticker) | 25/day | $0. Over ~25 tickers, spread the scan across 2 days, or pay ~$50/mo (Guessing on current price) |
| **Total** | | | **$0/month** |

## 5. Proposed scoring methodology (transparent, no black box)

Each component is scored on **−1…+1** and shown with its raw inputs.

**R: revision direction** (weekly, most tickers)
```
breadth = (up_30d − down_30d) / max(analyst_count, 1)          # current FY + next FY, averaged
drift   = (eps_avg_now − eps_avg_30d_ago) / |eps_avg_30d_ago|
R = clip(0.5·breadth + 0.5·clip(drift / 0.05, −1, 1), −1, 1)    # a 5% 30-day drift = full score
```

**B: backlog delta** (quarterly, industrial names only)
```
bb = 1 + ΔBacklog_qoq / Revenue_q           # implied book-to-bill, or the reported value if extracted
B  = clip((bb − 1) / 0.5, −1, 1)            # bb 1.5 = +1, bb 0.5 = −1
```

**I: insider cluster** (event)
```
n = distinct insiders with non-10b5-1 open-market buys ≥ $25k in the last 30 days
I = 0 if n < 2 else min(1, (n − 1) / 3) × officer_boost × sector_weight
officer_boost = 1.25 if CEO or CFO is among them
```

**Composite** = weighted mean **over available components only**, default weights R 0.5 / B 0.3 / I 0.2, reported with a coverage badge (e.g. "2/3 signals"). The ranked list shows **Δ composite vs. 4 weeks ago** next to the level, because a change in the signal is what the thesis cares about.

**Where I disagree with the brief:**
- **"Normalized per sector": I'd drop it.** With 15–30 tickers across 4–5 user-defined sectors, each sector has 3–6 names. Z-scoring within a group of 4 is noise, and it forces one name in every sector to rank "high" even when the whole sector is deteriorating. Use the absolute −1…+1 scales above, and give sector a role only through the insider `sector_weight`.
- **Sector weights for insider buys** (utilities/banks 1.0, industrials/materials 0.8, tech/semis 0.5) are **priors, not fitted values** (Guessing on the exact numbers; the directional ordering comes from the brief's cited research, which I haven't independently verified). They should be user-editable and labeled as such. Note that this down-weights the insider signal for most of your own watchlist.

## 6. Recommended stack

- **Backend:** Python 3.12 + FastAPI + SQLite (stdlib `sqlite3`, no ORM needed at this size) + a CLI `scan` command runnable from cron. Python because the work is XML/JSON/regex parsing.
- **Frontend:** Vite + React + TypeScript, built to static files served by FastAPI, installable as a PWA on iPhone to get the "premium iOS app" feel without App Store friction.
- **Deploy anywhere:** one Docker image, or `uvicorn` on any box. No platform lock-in.

## 7. Repo placement: decision needed

This branch lives in `bigbrands`, which is a Cloudflare Workers static site (`wrangler.jsonc` deploys `site/`). I put this work under `signal-scanner/`, which is **not** deployed by the existing config. A personal finance tool doesn't belong in a store's repo long term. I recommend moving it to its own repo before the build phase.

## Questions to confirm before the build

1. OK to make insider clusters an **event flag** plus 20% weight, rather than a primary pillar?
2. OK to **drop per-sector normalization** in favor of absolute scales?
3. Backlog: accept the **semi-manual "confirm extracted value"** flow for non-XBRL companies?
4. Separate repo, or keep building under `bigbrands/signal-scanner/`?
5. An Alpha Vantage free key is needed (free signup). The SEC User-Agent needs a contact email, which will come from config and not be hardcoded.
