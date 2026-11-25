# Project notes for Claude

## Edge Lab · Learn section must stay in sync
`trading-bot/edge-lab/public/js/learn/content.js` holds the Hebrew quant lessons shown in the local Edge Lab app
(`#learn`) and on the published Edge Lab page (served there as `learn.js`).
Whenever research changes something a lesson explains — a strategy's verdict or numbers, a gate, the Monte Carlo
method, the placebo tests, a new factory result — update the matching lesson (or add one) in the same change.
Lessons read live numbers from the registry, so after `python3 build.py` in `trading-bot/research/lab` most examples
update by themselves; check the prose around them still matches.

After a registry change: run `python3 build.py`, then republish the Edge Lab page with `data.json` and `learn.js`.
