# Eval engine — fastest realistic LucidFlex 50K pass (Databento MNQ 2020-01 → 2026-10)

ledger.py (5 edges, every trade, MAE) → sim.py (Lucid rules: +$3K, $2K trailing EOD locking at +$100, 50 % consistency;
intraday equity checked with each trade's MAE) → search.py (5,811 random policies, selected on attempts starting 2020–23,
checked on 2024–26) → analyze.py (block-bootstrap Monte Carlo, 2,000 paths).

| policy | pass 2020–23 | pass 2024–26 | bootstrap | days if pass | exp. days to 1st pass | exp. cost | win / trade | win / day |
|---|---|---|---|---|---|---|---|---|
| FAST: NA-FVG+NA+PF+PM, 10 MNQ, day cap $900, day stop $1,000, ≤ 2 trades | 23 % | 13 % | 19 % | 6–9 | 18–27 | $665–1,170 | 52–62 % | 49–57 % |
| BALANCED: all 5 edges, 1 MNQ, day stop $400 | 79 % | 50 % | 60 % | 42–49 | 60–66 | $190–300 | 60–65 % | 47–54 % |
If Lucid only measured the trailing limit at the close (no intraday breach), TEST pass rises to 31 % (FAST) / 62 % (BALANCED).
Regime guard: on 2012–2019 the underlying edges are ≈ 0 (research/longhist), so expect barrier/coin-flip odds there.
Findings: (1) size buys speed but the intraday drawdown kills big-size attempts — the "fast" policies are a lottery costing
$700–1,200 per pass; (2) win rate per trade ≈ 60–65 %, per day ≈ 50 %, planned R:R per trade 0.2–1.4 — no policy gives high
win AND high R:R; (3) every policy loses 10–30 pass-points from 2020–23 to 2024–26 (edges weakening).
