"""Run all 186 coded strategies (127 classic papers + 59 pre-2002 rules) on one market. Each market gets its own costs (bp of price)
and tick; P&L is stored as net RETURN (fraction of price) per day so markets can be mixed. Output: scratchpad/mpool/<SYM>.pkl"""
import sys, os, time
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, os.path.join(H, "../papers"), os.path.join(H, "../oldweb")]
import numpy as np, pandas as pd
import engine as E, mdata
OUT = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/mpool/"


def run(sym):
    D = mdata.load(sym); bp = D["bp"]; E.TICK = D["tick"]
    E.rt_cost = lambda px, cx=1.0: bp * 1e-4 * px * cx
    import strats as T1, rules as T2
    N = len(D["days"]); RET = E.day_returns(D); px = D["do"]; cols = {}

    def ser(o):
        s = np.zeros(N)
        if o[0] == "d":
            _, hold, mode = o; _, _, dpn, _ = E.daily_eval(hold, RET[mode], mode, px); s = np.nan_to_num(dpn)
        elif o[0] == "i":
            T = E.intraday_trades(D, o[1])
            if T: np.add.at(s, T["d"], T["net"])
        else:
            for x in o[1]:
                d, sd, fp, xp = x[:4]
                if np.isfinite(fp) and np.isfinite(xp): s[d] += sd * (xp - fp) - E.rt_cost(fp)
        return s / px
    for r in T1.REG:
        try: cols[f"P{r['sid']}:{r['name']}"] = ser(r["fn"](D, 1.0))
        except Exception as e: pass
    for r in T2.REG:
        if r["rid"] >= 52: continue                     # moon/weather/astro rules: NQ-specific data, not re-run per market
        try: cols[f"W{r['rid']}:{r['name']}"] = ser(r["fn"](D))
        except Exception as e: pass
    P = pd.DataFrame(cols, index=D["days"]); P.attrs["bh"] = pd.Series(np.r_[0, np.diff(D["dc"])] / px, index=D["days"])
    os.makedirs(OUT, exist_ok=True); pd.to_pickle(dict(P=P, bh=P.attrs["bh"]), OUT + sym + ".pkl"); return P.shape


if __name__ == "__main__":
    for s in sys.argv[1:]:
        t0 = time.time(); print(s, run(s), f"{time.time() - t0:.0f}s", flush=True)
