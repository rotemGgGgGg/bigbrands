exec(open("placebo.py").read().split('print("per market:")')[0])
u = port(False, rng); raw = pd.Series(0.0, index=idx)
for sym, ix, X, zz, S in data: raw = raw.add(pd.Series(X.sum(1), index=ix), fill_value=0)
Y = idx.year
for a, b in ((2012, 2019), (2020, 2022), (2023, 2026)):
    m = (Y >= a) & (Y <= b); print(f"{a}-{b}: unfiltered {sh(raw[m]):.2f}  filtered {sh(u[m]):.2f}")
print("per-year filtered minus unfiltered (Sharpe):", {y: round(sh(u[Y==y]) - sh(raw[Y==y]), 2) for y in range(2020, 2027)})
print(f"days traded share: unfiltered {(raw!=0).mean():.2f} filtered {(u!=0).mean():.2f}")
