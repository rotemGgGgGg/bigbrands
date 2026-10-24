"""Smoke test: every template at its own defaults (stop/target ATR from the .pine file), 15-minute bars, 24 h and RTH."""
import time, numpy as np, pandas as pd
import bars, signals as G, engine as E
DEF = {1: (2.0, 1.0), 2: (1.8, 0.9), 3: (1.5, 1.0), 4: (1.5, 1.2), 5: (1.8, 1.2), 6: (1.7, 0.8), 7: (1.7, 1.0), 8: (1.5, 0.9),
       9: (1.5, 1.2), 10: (1.6, 0.9)}


def stats(yr, R):
    out = {}
    for nm, m in (("tr", yr <= 2019), ("va", (yr >= 2020) & (yr <= 2023)), ("te", yr >= 2024)):
        r = R[m]; out[nm + "_n"] = len(r); out[nm + "_R"] = r.mean() if len(r) else np.nan
        out[nm + "_win"] = 100 * (r > 0).mean() if len(r) else np.nan
        out[nm + "_t"] = r.mean() / r.std() * np.sqrt(len(r)) if len(r) > 2 and r.std() > 0 else np.nan
    return out


if __name__ == "__main__":
    tf = 15; B = G.prepare(bars.build(tf), tf); yr = pd.DatetimeIndex(B["day"]).year.values; rows = []
    for sid in range(1, 51):
        t0 = time.time(); L, S = G.signals(B, sid, 1.0, 0); sl, tp = DEF.get(sid, (1.5, 1.0)); t1 = time.time()
        for sess in (0, 1):
            i, x, R, sd = E.sim(B["o"], B["h"], B["l"], B["c"], B["atr"], B["mod"], B["roll"], L, S, sl, tp, 0, sess, 1.0)
            rows.append(dict(sid=sid, sess=sess, sigL=int(L.sum()), sigS=int(S.sum()), sig_s=round(t1 - t0, 2), **stats(yr[i], R)))
    pd.set_option("display.width", 250); pd.set_option("display.max_rows", 200)
    print(pd.DataFrame(rows).round(3).to_string(index=False))
