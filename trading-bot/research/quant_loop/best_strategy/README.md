# Best strategy (PROVISIONAL): Pre-Open Fade 1:2
Rules: config.json. Reproduce: `python trading-bot/research/quant_loop/best_strategy/run.py` → run_output.txt.
Depends on trading-bot/research/hunt/prefade.py and the Databento pickles described in ../research_state.md.
Pine version (1:0.5 variant, 76 % wins): trading-bot/pine/preopen_fade.pine — set Target = 1.0, Stop = 1.0 → 0.5 and |z| = 2.5 for this 1:2 variant.
