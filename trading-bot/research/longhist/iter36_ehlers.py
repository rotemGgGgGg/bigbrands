"""Iter 38 (queue) — John Ehlers' Hilbert-transform tools ('Rocket Science for Traders', 2001): Sine-wave indicator (Sine /
LeadSine crossings = cycle turning points) used ONLY in cycle mode (dominant cycle period stable: |ΔP| < 15 % over the last half
cycle), and the Instantaneous Trendline crossover for trend mode. RTH bars of 5 and 15 minutes concatenated across days.
Trade: the first signal after 10:00 (until 15:00), market at the next bar's open, stop k·σ_day, target 2k·σ_day, exit close.
Three periods 2012–19 (NSXUSD) / 2020–23 / 2024–26 (Databento), costs 2.25 pt scaled to price."""
import sys; sys.path[:0] = [".", "..", "../influencers"]
import numpy as np, pandas as pd, itertools, math
exec(open("iter26_web.py").read().split("\nres = []")[0])
def ehlers(p):
    n = len(p); S = np.zeros(n); Det = np.zeros(n); I1 = np.zeros(n); Q1 = np.zeros(n); I2 = np.zeros(n); Q2 = np.zeros(n)
    Re = np.zeros(n); Im = np.zeros(n); P = np.full(n, 15.0); SP = np.full(n, 15.0); sine = np.zeros(n); lead = np.zeros(n)
    it = np.zeros(n); tl = p.copy()
    for t in range(6, n):
        S[t] = (4 * p[t] + 3 * p[t - 1] + 2 * p[t - 2] + p[t - 3]) / 10
        a = 0.075 * P[t - 1] + 0.54
        Det[t] = (0.0962 * S[t] + 0.5769 * S[t - 2] - 0.5769 * S[t - 4] - 0.0962 * S[t - 6]) * a
        Q1[t] = (0.0962 * Det[t] + 0.5769 * Det[t - 2] - 0.5769 * Det[t - 4] - 0.0962 * Det[t - 6]) * a
        I1[t] = Det[t - 3]
        jI = (0.0962 * I1[t] + 0.5769 * I1[t - 2] - 0.5769 * I1[t - 4] - 0.0962 * I1[t - 6]) * a
        jQ = (0.0962 * Q1[t] + 0.5769 * Q1[t - 2] - 0.5769 * Q1[t - 4] - 0.0962 * Q1[t - 6]) * a
        I2[t] = 0.2 * (I1[t] - jQ) + 0.8 * I2[t - 1]; Q2[t] = 0.2 * (Q1[t] + jI) + 0.8 * Q2[t - 1]
        Re[t] = 0.2 * (I2[t] * I2[t - 1] + Q2[t] * Q2[t - 1]) + 0.8 * Re[t - 1]
        Im[t] = 0.2 * (I2[t] * Q2[t - 1] - Q2[t] * I2[t - 1]) + 0.8 * Im[t - 1]
        pp = 360 / math.degrees(math.atan(Im[t] / Re[t])) if Im[t] != 0 and Re[t] != 0 else P[t - 1]
        pp = min(max(pp, 0.67 * P[t - 1], 6), 1.5 * P[t - 1], 50); P[t] = 0.2 * pp + 0.8 * P[t - 1]
        SP[t] = 0.33 * P[t] + 0.67 * SP[t - 1]; dc = int(SP[t] + 0.5)
        if t < dc + 1: continue
        w = np.arange(dc); seg = S[t - w]
        rp = np.sum(np.sin(np.radians(360 * w / dc)) * seg); ip = np.sum(np.cos(np.radians(360 * w / dc)) * seg)
        ph = math.degrees(math.atan(rp / ip)) if abs(ip) > 1e-12 else (90 if rp > 0 else -90)
        ph += 90; ph += 360 / SP[t] if True else 0
        if ip < 0: ph += 180
        if ph > 315: ph -= 360
        sine[t] = math.sin(math.radians(ph)); lead[t] = math.sin(math.radians(ph + 45))
        it[t] = p[t - dc + 1:t + 1].mean(); tl[t] = (4 * it[t] + 3 * it[t - 1] + 2 * it[t - 2] + it[t - 3]) / 10
    return SP, sine, lead, tl
res = []
for per, o, h, l, c, dow in grids():
    N = len(o); O = o[:, 0]; C = c[:, 389]; sig = pd.Series(np.abs(C / O - 1)).rolling(14).mean().shift().values
    for tf in (5, 15):
        nb = 390 // tf; cl = c[:, tf - 1::tf][:, :nb].ravel()
        SP, sine, lead, tl = ehlers(cl.astype(float))
        stab = np.r_[np.zeros(10), np.abs(SP[10:] / SP[:-10] - 1)] < 0.15
        up_x = (lead > sine) & (np.r_[0, lead[:-1]] <= np.r_[0, sine[:-1]])
        dn_x = (lead < sine) & (np.r_[0, lead[:-1]] >= np.r_[0, sine[:-1]])
        tr_up = (cl > tl) & (np.r_[0, cl[:-1]] <= np.r_[0, tl[:-1]]); tr_dn = (cl < tl) & (np.r_[0, cl[:-1]] >= np.r_[0, tl[:-1]])
        sigs = {"sine cycle-mode": np.where(up_x & stab, 1, np.where(dn_x & stab, -1, 0)),
                "sine any": np.where(up_x, 1, np.where(dn_x, -1, 0)),
                "trendline trend-mode": np.where(tr_up & ~stab, 1, np.where(tr_dn & ~stab, -1, 0))}
        for (nm, sg), k in itertools.product(sigs.items(), (0.15, 0.25, 0.4)):
            sg = sg.reshape(N, nb); R = []
            for i in range(15, N):
                if not np.isfinite(sig[i]): continue
                b0 = 30 // tf; b1 = 330 // tf; ix = np.nonzero(sg[i, b0:b1])[0]
                if not len(ix): continue
                b = b0 + ix[0]; s = int(sg[i, b]); m = (b + 1) * tf; e = o[i, m]; st = k * sig[i] * e
                px, _, _ = walk(o[i], h[i], l[i], c[i], m, s, e, e - s * st, e + s * 2 * st, 389)
                R.append((s * (px - e) - 2.25 * e / 17000) / st)
            R = np.array(R)
            res.append(dict(per=per, rule=f"{nm} {tf}m k{k}", n=len(R), win=round(100 * (R > 0).mean(), 1), R=round(R.mean(), 3)))
    print(per, "done", flush=True)
T = pd.DataFrame(res); T.to_csv("iter36_ehlers.csv", index=False)
W = T.pivot_table(index="rule", columns="per", values=["win", "R", "n"]); W["minR"] = W["R"].min(axis=1); W["minwin"] = W["win"].min(axis=1)
pd.set_option("display.width", 250); print(W.sort_values("minR", ascending=False).round(3).to_string())
