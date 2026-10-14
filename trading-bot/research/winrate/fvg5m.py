"""NA-FVG with the gap found on 5-minute candles (so it can run on a 5m TradingView chart with 2 years of history).
Same break, same bracket; fill = price trades through the gap edge by a tick; exits walked on 1-minute bars."""
from signals import *
from deep import stats
from conservative import bracket_c

def sig_na_fvg5(window=60, tf=5):
    out = []
    for i, k0, s, _ in sig_na_first():
        h, l = D.h[i], D.l[i]
        gap = None
        b0 = k0 // tf                                       # first 5m bar after the break
        for b in range(b0 + 2, min((k0 + window) // tf, 388 // tf)):
            hb = lambda x: h[x * tf:(x + 1) * tf].max(); lb_ = lambda x: l[x * tf:(x + 1) * tf].min()
            if (s == 1 and hb(b - 2) < lb_(b)) or (s == -1 and lb_(b - 2) > hb(b)):
                gap = lb_(b) if s == 1 else hb(b)
                j0 = (b + 1) * tf                           # gap known at the 5m close
                j = next((x for x in range(j0, min(k0 + window, 388)) if ((l[x] <= gap) if s == 1 else (h[x] >= gap))), None)
                if j is not None: out.append((i, j, s, gap))
                break
    return out

if __name__ == "__main__":
    for nm, sg in (("1m FVG", sig_na_fvg()), ("5m FVG", sig_na_fvg5())):
        for a, b in ((0.15, 2.0), (0.2, 2.0), (0.25, 2.0)):
            print(nm, a, b, stats(bracket_c(sg, a, b)))
