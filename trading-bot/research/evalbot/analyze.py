"""Pick policies from the search (selected on 2020–23 starts), show their 2024–26 check, then a block-bootstrap Monte Carlo
(20-day blocks, 2,000 synthetic histories) for the finalists."""
import sys, os, glob, json; H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, H)
import numpy as np, pandas as pd
from ledger import load
from sim import Book, attempt, FEE
R = pd.concat([pd.read_csv(f) for f in glob.glob(os.path.join(H, "search_*.csv"))], ignore_index=True).drop_duplicates("policy")
print("policies evaluated:", len(R))
R = R[R.tr_n_attempts >= 100]
fast = R.sort_values("tr_exp_days").head(15)
cheap = R[R.tr_exp_days <= 60].sort_values("tr_exp_cost").head(10)
pd.set_option("display.width", 250); pd.set_option("display.max_colwidth", 140)
cols = ["policy", "tr_pass_pct", "tr_days_pass", "tr_exp_days", "tr_exp_cost", "tr_trade_win", "tr_day_win", "te_pass_pct", "te_days_pass", "te_exp_days", "te_exp_cost"]
print("\nFASTEST (by expected days to first pass, selected on 2020–23):"); print(fast[cols].to_string(index=False))
print("\nCHEAPEST with expected ≤ 60 trading days:"); print(cheap[cols].to_string(index=False))
L = load(); B = Book(L); rng = np.random.default_rng(7)
def bootstrap(pol, n=2000, block=20):
    nd = len(B.days); out = []
    orig = B.by_edge
    for _ in range(n):
        order = []
        while len(order) < 300:
            s = rng.integers(0, nd - block); order += list(range(s, s + block))
        B.by_edge = {e: [orig[e][k] for k in order] for e in orig}; B_days = B.days; B.days = np.arange(len(order))
        r = attempt(B, 0, pol, max_days=299); B.days = B_days
        if r[0] is not None: out.append(r)
    B.by_edge = orig
    P = np.mean([r[0] for r in out]); dp = np.mean([r[1] for r in out if r[0]]); df = np.mean([r[1] for r in out if not r[0]]) if P < 1 else 0
    return dict(boot_pass=round(100 * P, 1), boot_days_pass=round(dp, 1), boot_exp_days=round((1 - P) / P * df + dp, 1), boot_exp_cost=round(FEE / P))
fin = pd.concat([fast.head(3), cheap.head(3)]).drop_duplicates("policy")
print("\nBOOTSTRAP (finalists):")
for p in fin.policy:
    print(p, bootstrap(json.loads(p)))
fin.to_csv(os.path.join(H, "finalists.csv"), index=False)
