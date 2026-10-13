# Prop plan — LucidFlex 50K with Noise-Area (simulated 2020–2026)

## Account rules used (third-party summaries, Oct 2026 — verify on lucidtrading.com before buying)
Eval: +$3,000 target · $2,000 EOD-trailing max loss (locks at +$100 once EOD ≥ +$2,100) · best day ≤ 50 % of profit ·
one-time fee ≈ $146 list (≈ $90–105 with codes) · DLL optional (we choose OFF) · flat by 16:45 ET.
Funded: same max loss · payout after 5 days ≥ $150 and a positive cycle · request $500 … min(50 % of profit, $2,000) ·
90 % to trader · a request locks the max loss at +$100 · up to 5 sim payouts.

## The plan
1. Strategy: Noise-Area (pine/noise_area.pine), **1 MNQ**, no daily stop (every daily stop tested made it worse out-of-sample).
2. Evaluation: trade every day until profit ≥ $3,000 **and** best day ≤ 50 % of it; then stop.
3. Funded: request a payout only when, after the request, **$2,500 of profit stays in the account**
   (request = min($2,000, 50 % of profit, profit − $2,500), and ≥ $500, after 5 days ≥ $150).

## Simulated results (every start day; chosen on 2020–23 starts, checked on 2024–26 starts)
| | 2020–23 starts | 2024–26 starts* |
|---|---|---|
| Pass the evaluation | 59.9 % | 85.1 % |
| Get ≥ 1 payout | 49.2 % | 39.9 % |
| Average payouts | 2.25 | 0.83 |
| Reach 5 payouts | 39.0 % | 8.8 % |
| Expected value per attempt (payouts × 90 % − $146) | **+$1,457** | **+$609** |
| Median time to pass | ≈ 6–7 months | |

\* 2024–26 starts are cut short by the end of the data (Oct 2026), so payouts there are undercounted.

## What did not help (all tested)
2–3 MNQ (faster but pass 30–49 %, EV lower or negative) · daily stops $300–1,000 · adding IB breakout ·
withdrawing as soon as allowed (keep $0: EV +$348 / +$286 — the post-payout lock leaves only $400 of room).

Files: prop_sim.py, prop_sim2.py, prop_sim_na.csv, prop_sim2.csv.
