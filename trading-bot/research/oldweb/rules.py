"""Stage 4 - every concrete rule found in the pre-2002 corpus, coded as the poster wrote it (their numbers; point sizes from
1990s S&P/T-bond/SPI converted to the same % of price). Source = newsgroup, year, the poster's sentence (shortened).
Each fn(D) returns ('d', hold, mode) for the daily engine, ('i', spec) for the intraday engine, or ('t', trades) for
rules that need a per-day loop (trailing stops, re-entries)."""
import sys, os
import numpy as np, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "papers"))
from strats import sma, ema, hh, ll, lag, rsi, xo, xu, nz, state, hold_n, sig, month_end, blank, oco, pdh, S
REG = []


def reg(name, src, kind="d"):
    def w(f): REG.append(dict(rid=len(REG) + 1, name=name, src=src, kind=kind, fn=f)); return f
    return w


def dly(D): return D["do"], D["dh"], D["dl"], D["dc"]
def stoch(h, l, c, n, k=1, d=3):
    raw = 100 * (c - ll(l, n)) / np.maximum(hh(h, n) - ll(l, n), 1e-9)
    K = sma(raw, k) if k > 1 else raw; return K, sma(K, d)
def single(D, cond, side, lvl, stop=None, tgt=None, e=0, kind=1, tx=389):
    sp = blank(D, kind); ok = nz(cond) & ~np.isnan(lvl); sp["dir"][ok] = side; sp["e"][:] = e
    k = "L" if side > 0 else "S"; sp["lvl" + k] = lvl
    if stop is not None: sp["stop" + k] = stop
    if tgt is not None: sp["tgt" + k] = tgt
    sp["tx"][:] = tx; return ("i", sp)
def both(D, a, b):
    """two single-direction specs on different days merged into one OCO-free spec (days never overlap by construction)."""
    sa, sb = a[1], b[1]; sp = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in sa.items()}
    m = sb["dir"] != 0; sp["dir"][m] = sb["dir"][m]
    for k in ("lvlS", "stopS", "tgtS"): sp[k] = np.where(m, sb[k], sp[k])
    return ("i", sp)


# ---------------------------------------------------------------- gap / open rules
@reg("OOPS (Williams): gap beyond prior H/L, stop entry back at it, exit close",
     "misc.invest.futures 1997 'Index Trading System!' (Badcock) + 2001 'Help with easy language': if open < low 1 bar ago buy at low+1 tick", "i")
def f(D):
    o = D["do"]; ph, pl, _ = pdh(D)
    return both(D, single(D, o < pl, 1, pl + 0.25, stop=np.full(len(o), np.nan)), single(D, o > ph, -1, ph - 0.25, stop=np.full(len(o), np.nan)))

@reg("OOPS held overnight (exit next open)", "misc.invest.futures 1997: 'wait until the next day's open to exit ... profitability increased by as much as 50%'", "t")
def f(D):
    o, h, l, c = dly(D); ph, pl, _ = pdh(D); out = []
    for t in range(1, len(o) - 1):
        if o[t] < pl[t] and h[t] >= pl[t] + 0.25: out.append((t, 1, pl[t] + 0.25, o[t + 1]))
        elif o[t] > ph[t] and l[t] <= ph[t] - 0.25: out.append((t, -1, ph[t] - 0.25, o[t + 1]))
    return ("t", out)

@reg("Connors 10% OOPS: close in bottom/top 10% of range, gap beyond, stop entry at prior L/H",
     "misc.invest.futures 1998 'Traders Electronic Magazine #4': close in bottom 10% of range and gap lower -> buy if it trades back above", "i")
def f(D):
    o, h, l, c = dly(D); pos = lag((c - l) / np.maximum(h - l, 1e-9)); ph, pl, _ = pdh(D)
    return both(D, single(D, (pos <= .1) & (o < pl), 1, pl, stop=np.full(len(o), np.nan)),
                single(D, (pos >= .9) & (o > ph), -1, ph, stop=np.full(len(o), np.nan)))

@reg("Gap fade to prior close: open beyond prior close -> fade at open, target prior close, exit close",
     "misc.invest.futures 1999 'How to Know an Open Probability': 85% of the time after any opening prices retrace to the previous close", "i")
def f(D):
    o = D["do"]; _, _, pc = pdh(D); n = len(o)
    up = single(D, o > pc, -1, o, tgt=pc, kind=0); dn = single(D, o < pc, 1, o, tgt=pc, kind=0); return both(D, dn, up)

@reg("Open +/- 0.29% breakout (Paragon), stop at open, exit close", "misc.invest.futures 1998 Paragon Traders' Report: 'enter long if the S&Ps moved 3.30 points above the open'", "i")
def f(D):
    o = D["do"]; k = o * 0.0029; return oco(D, o + k, o - k, np.ones(len(o), bool), stopL=o, stopS=o)

@reg("Bull/Bear power stops from the open (Bear = H-C, Bull = C-L of yesterday), exit close",
     "misc.invest.futures 1998: 'Let Bull Power = Close - Low; Bear Power = High - Close. Tomorrow after the open place a buy stop bear power up from the open'", "i")
def f(D):
    o, h, l, c = dly(D); bp = lag(h - c); bl = lag(c - l); return oco(D, o + bp, o - bl, np.ones(len(o), bool), stopL=o - bl, stopS=o + bp)

@reg("SPI 'Grab'n'Run': buy every open, stop -1.1%, target +1.4%, exit close", "misc.invest.futures 2000 'BUYING the SPI on the Open': StopLoss Open-34, Grab'n'Run Open+42 (SPI ~3050)", "i")
def f(D):
    o = D["do"]; return single(D, np.ones(len(o), bool), 1, o, stop=o * (1 - .011), tgt=o * (1 + .014), kind=0)

@reg("Buy every open, sell at +8 ticks (0.25%), else close", "misc.invest.futures 2002 'Is it a good idea?': buy at the open every day and sell as soon as it hits 8 ticks", "i")
def f(D):
    o = D["do"]; return single(D, np.ones(len(o), bool), 1, o, tgt=o * 1.0025, kind=0)

@reg("Early-session reversal: -0.4% under prior close in first 90 min -> 0.27% trailing buy stop; +0.4% -> 0.4% trailing sell stop; exit close",
     "misc.invest.technical 1997: 'first 1 1/2 hours if the S&P trades -300 points from yesterday's close buy using a 200 point trailing buy stop' (S&P ~750)", "t")
def f(D):
    O, H, L, C = D["o"], D["h"], D["l"], D["c"]; pc = lag(D["dc"]); out = []
    for t in range(1, len(pc)):
        lo, hi, done = 1e18, -1e18, False
        for m in range(90):
            lo = min(lo, L[t, m]); hi = max(hi, H[t, m])
            if lo <= pc[t] * (1 - .004) and H[t, m] >= lo * 1.0027 and m > 0:
                out.append((t, 1, max(lo * 1.0027, O[t, m]), C[t, -1], m)); break
            if hi >= pc[t] * (1 + .004) and L[t, m] <= hi * (1 - .004) and m > 0:
                out.append((t, -1, min(hi * (1 - .004), O[t, m]), C[t, -1], m)); break
    return ("t", [x[:4] for x in out])

@reg("Opening-range failure reversal: break of the 15-min range one way before 10:10, re-entry and break of the other side -> go with it, stop other side, exit close",
     "misc.invest.futures 2000 'DAX Daytraders': within 20-40 mins the market reverses, re-enters the opening range, then penetrates beyond the range in the other direction, I go with that move", "t")
def f(D):
    O, H, L, C = D["o"], D["h"], D["l"], D["c"]; out = []
    for t in range(len(O)):
        hi, lo = H[t, :15].max(), L[t, :15].min(); first = 0
        for m in range(15, 330):
            if first == 0 and m < 40:
                if H[t, m] > hi: first = 1
                elif L[t, m] < lo: first = -1
                continue
            if first == 1 and L[t, m] < lo: out.append((t, -1, min(lo, O[t, m]), None, m, hi)); break
            if first == -1 and H[t, m] > hi: out.append((t, 1, max(hi, O[t, m]), None, m, lo)); break
            if first == 0: break
    res = []
    for t, sd, fp, _, m, st in out:
        x = C[t, -1]
        for k in range(m, 390):
            if (sd > 0 and L[t, k] <= st) or (sd < 0 and H[t, k] >= st): x = st if k > m else fp; break
        res.append((t, sd, fp, x))
    return ("t", res)


# ---------------------------------------------------------------- range / pattern rules
@reg("NR7 day -> next day buy/sell stop at prior H/L, stop other side, exit close", "misc.invest.futures 1999 'T-Bond Day Trading': TODAY IS AN NR7 DAY, if YH is exceeded buy the breakout", "i")
def f(D):
    r = D["dh"] - D["dl"]; ph, pl, _ = pdh(D); return oco(D, ph, pl, lag(r <= ll(r, 7)))

@reg("NR4 day -> next day prior H/L breakout, exit close", "misc.invest.futures 1999 'Day Trading Sep T-Bonds': NR4 SIGNAL, if YH is exceeded buy the breakout", "i")
def f(D):
    r = D["dh"] - D["dl"]; ph, pl, _ = pdh(D); return oco(D, ph, pl, lag(r <= ll(r, 4)))

@reg("Close in bottom 20% of the day's range -> long next day open->close (top 20% -> short)",
     "misc.invest.futures 1999: 'a C<=20% Of The Day's Range signal working for us' (expects a higher close)", "d")
def f(D):
    o, h, l, c = dly(D); pos = (c - l) / np.maximum(h - l, 1e-9); return ("d", lag(np.where(pos <= .2, 1, np.where(pos >= .8, -1, 0))), "oc")

@reg("Gann pullback: uptrend (close > 200d SMA) + 3 lower lows (or 2 lower lows + inside day) -> buy stop above prior high, stop prior low, exit close",
     "misc.invest.futures 1998 'What is a market turn?': Gann's pullback entry rule is 3 days of lower lows or 2 lower lows & an inside day; 1997: buy a breakout of the previous day's high IF in a larger uptrend after 3-4 lower lows", "i")
def f(D):
    o, h, l, c = dly(D); ll1 = l < lag(l); ins = (h < lag(h)) & (l > lag(l))
    up = c > sma(c, 200); dn = c < sma(c, 200); hl1 = h > lag(h); ins2 = ins
    cl = nz(up) & ((nz(ll1) & nz(lag(ll1)) & nz(lag(ll1, 2))) | (nz(ll1) & nz(lag(ll1)) & nz(ins2)) | (nz(ins2) & nz(lag(ll1)) & nz(lag(ll1, 2))))
    cs = nz(dn) & ((nz(hl1) & nz(lag(hl1)) & nz(lag(hl1, 2))) | (nz(hl1) & nz(lag(hl1)) & nz(ins2)) | (nz(ins2) & nz(lag(hl1)) & nz(lag(hl1, 2))))
    ph, pl, _ = pdh(D)
    return both(D, single(D, nz(lag(cl)), 1, ph, stop=pl), single(D, nz(lag(cs)) & ~nz(lag(cl)), -1, pl, stop=ph))

@reg("5-day range 20% re-entry: close below 20% of the 5-day range then back above -> long (mirror short), stop-and-reverse",
     "misc.invest.technical 1995: 'the old program I dug up on a BBS CD which buys when the close has gone below 20% of the range of the last five days' High-Low range then back above (and obverse for shorting)'", "d")
def f(D):
    o, h, l, c = dly(D); p = (c - ll(l, 5)) / np.maximum(hh(h, 5) - ll(l, 5), 1e-9)
    bl = nz((p > .2) & (lag(p) <= .2)); bs = nz((p < .8) & (lag(p) >= .8)); return sig(state(bl, bs, bs, bl))


# ---------------------------------------------------------------- oscillators / averages (daily, stop-and-reverse unless noted)
@reg("Hershey stochastic (5,2,3) enters 75% zone -> long, enters 25% -> short", "misc.invest.futures 2002 'Jack: Please read': Enter long: Stochastic (5,2,3) enters the 75% Zone", "d")
def f(D):
    o, h, l, c = dly(D); K, Dd = stoch(h, l, c, 5, 2, 3); u = nz((K > 75) & (lag(K) <= 75)); d = nz((K < 25) & (lag(K) >= 25))
    return sig(state(u, d, d, u))

@reg("Stochastic 5,2,2 fast line enters 80 -> long, exits 80 -> flat; enters/exits 20 short", "misc.invest.futures 2002 'Question for Jack Hershey: Stochastics once again'", "d")
def f(D):
    o, h, l, c = dly(D); K, _ = stoch(h, l, c, 5, 2, 2)
    return sig(state(nz((K > 80) & (lag(K) <= 80)), nz(K < 80), nz((K < 20) & (lag(K) >= 20)), nz(K > 20)))

@reg("Stochastic 14,3: %K crosses up %D below 30 -> buy, crosses down above 70 -> sell", "misc.invest.technical 1996: 'If SK<30 and SD<30 and SK<SD and SK next period > SD then buy'", "d")
def f(D):
    o, h, l, c = dly(D); K, Dd = stoch(h, l, c, 14, 1, 3); u = nz(xo(K, Dd) & (lag(K) < 30)); d = nz(xu(K, Dd) & (lag(K) > 70))
    return sig(state(u, d, d, u))

@reg("Close vs upper/lower Bollinger (20,2): close above -> buy next open, below -> short", "misc.invest.futures 1999: 'So if it closes above the upper band, we buy the next open'", "d")
def f(D):
    c = D["dc"]; m = sma(c, 20); s = S(c).rolling(20).std().values; u = nz(c > m + 2 * s); d = nz(c < m - 2 * s); return sig(state(u, d, d, u))

@reg("Close above/below floor pivot (H+L+C)/3 -> long/short on the close", "misc.invest.futures 1999: 'When it closes above the pivot, buy on the close ... below the pivot, sell on the close'", "d")
def f(D):
    o, h, l, c = dly(D); pv = lag((h + l + c) / 3); return ("d", lag(np.sign(c - pv)), "cc")

@reg("40-day MA cross (long/short)", "misc.invest.technical 1995: 'A buy signal would be generated if the share price ... crossed over the 40-day moving average'", "d")
def f(D): c = D["dc"]; return sig(np.sign(c - sma(c, 40)))

@reg("35-day MA: short below / long above", "misc.invest.technical 1995: 'Sell and go short when close goes below 35 day ave'", "d")
def f(D): c = D["dc"]; return sig(np.sign(c - sma(c, 35)))

@reg("15-day MA closes (long/short)", "misc.invest.technical 2001: 'a 15 Day moving average ... buy and sell on closes beyond that moving average'", "d")
def f(D): c = D["dc"]; return sig(np.sign(c - sma(c, 15)))

@reg("5/10-day MA cross (long/short)", "misc.invest.futures 1998 'Characteristics of a Sound Trading Method': if our 5 day MA crosses over our 10 day MA we place a buy order", "d")
def f(D): c = D["dc"]; return sig(np.sign(sma(c, 5) - sma(c, 10)))

@reg("8/20-day MA cross (long/short)", "misc.invest.futures 1999 'Adaptive Trading': buy when the 8 day crosses above the 20 day", "d")
def f(D): c = D["dc"]; return sig(np.sign(sma(c, 8) - sma(c, 20)))

@reg("200-day SMA long/flat", "misc.invest.futures 2002: 'I buy when the stock exceeds its 200 day SMA ... sell when it closes below'", "d")
def f(D): c = D["dc"]; return sig((c > sma(c, 200)).astype(float))

@reg("Channel breakout 89/13 (enter beyond 89-day extreme, exit beyond 13-day)", "misc.invest.futures 1999 'Betsizing beats buy-and-hold': Channel Breakout entry 89 days, exit 13 days", "d")
def f(D):
    o, h, l, c = dly(D); return sig(state(nz(h > lag(hh(h, 89))), nz(l < lag(ll(l, 13))), nz(l < lag(ll(l, 89))), nz(h > lag(hh(h, 13)))))

@reg("Turtle 20-day breakout filtered by 20 vs 40-day MA", "misc.invest.futures 1998 'Trading discussion': if the 20 day is below the 40 day look for 20 day breakouts on the short side", "d")
def f(D):
    o, h, l, c = dly(D); tr = sma(c, 20) > sma(c, 40)
    return sig(state(nz((c > lag(hh(h, 20))) & tr), nz(c < lag(ll(l, 10))), nz((c < lag(ll(l, 20))) & ~tr), nz(c > lag(hh(h, 10)))))

@reg("21-day MA +/-3.5% band fade: close above +3.5% -> short until back at MA; below -3.5% -> long",
     "misc.invest.futures 1998 'The Correction Is Coming': DJIA inside 3.5% of its 21DMA about 85% of the time", "d")
def f(D):
    c = D["dc"]; m = sma(c, 21); return sig(state(nz(c < m * .965), nz(c >= m), nz(c > m * 1.035), nz(c <= m)))


# ---------------------------------------------------------------- calendar
@reg("NDX down >= 3% on Monday -> buy close, sell Tuesday close", "misc.invest.futures 2000: 'since 1983 when the NDX drops 3% or greater on a Monday the following Tuesday was an up day 69%'", "d")
def f(D):
    c = D["dc"]; r = c / lag(c) - 1; mon = D["days"].weekday.values == 0; return ("d", lag(np.where(nz(mon & (r <= -.03)), 1, 0)), "cc")

@reg("Buy close of 2nd Friday of month, exit first profitable open (stop -1%)", "misc.invest.futures 1999: 'Buy the S&P on the close of the second Friday of each month; $5,000 stop or exit on the first profitable opening'", "t")
def f(D):
    d = D["days"]; o, h, l, c = dly(D); fri = d.weekday.values == 4; out = []
    sec = fri & (d.day.values >= 8) & (d.day.values <= 14)
    for t in np.nonzero(sec)[0]:
        e = c[t]; st = e * .99
        for k in range(t + 1, min(t + 30, len(c))):
            if o[k] <= st: out.append((t, 1, e, o[k])); break
            if o[k] > e: out.append((t, 1, e, o[k])); break
            if l[k] <= st: out.append((t, 1, e, st)); break
    return ("t", out)

@reg("Month/weekday seasonal: long Mon open->Fri close in Jan/Apr/Aug; short Thu close->Mon open in Feb/Jun/Jul/Oct/Nov",
     "misc.invest.futures 1999: 'Buy on Mondays and sell on Fridays in January, April and August; Sell on Thursday and buy back Monday in February, June, July, October and November'", "t")
def f(D):
    d = D["days"]; o, h, l, c = dly(D); wd = d.weekday.values; mo = d.month.values; out = []
    for t in range(len(c)):
        if wd[t] == 0 and mo[t] in (1, 4, 8):
            k = t
            while k + 1 < len(c) and wd[k + 1] > wd[k]: k += 1
            if wd[k] == 4: out.append((t, 1, o[t], c[k]))
        if wd[t] == 3 and mo[t] in (2, 6, 7, 10, 11):
            k = t + 1
            while k < len(c) and wd[k] != 0 and wd[k] > wd[t]: k += 1
            if k < len(c) and wd[k] == 0 and k - t <= 3: out.append((t, -1, c[t], o[k]))
    return ("t", out)

@reg("Weekend effect: long Monday open -> Monday close", "misc.invest.futures 1999: 'people tend to sell stocks on friday close and buy them on monday open'", "d")
def f(D): return ("d", (D["days"].weekday.values == 0).astype(float), "oc")

@reg("Seasonal: long Nov-Apr, flat May-Oct", "misc.invest.futures 1998: 'entering the most bullish seasonal period for the stock market which has been profitable 80% of the time' (Oct/Nov)", "d")
def f(D):
    m = D["days"].month.values; return ("d", np.isin(m, (11, 12, 1, 2, 3, 4)).astype(float), "oo")


# ---------------------------------------------------------------- batch 2 (misc.invest / alt.invest)
@reg("Turn of month: buy close of 2nd-to-last day, sell close of 4th day of next month", "misc.invest 1990s: 'buy a stock market index fund at the close of the second-to-last day of each month and sell at the close of the fourth day of the next month'", "t")
def f(D):
    d = D["days"]; c = D["dc"]; me = np.nonzero(month_end(D))[0]; out = []
    for k in me:
        if k - 1 >= 0 and k + 4 < len(c): out.append((k - 1, 1, c[k - 1], c[k + 4]))
    return ("t", out)

@reg("S&P opens up -> buy the opening, stop -0.65%, exit close", "misc.invest 1994: 'If the S&P opens up, then Position traders should buy the opening, and use a 300 point stop' (S&P ~460)", "i")
def f(D):
    o = D["do"]; _, _, pc = pdh(D); return single(D, o > pc, 1, o, stop=o * (1 - .0065), kind=0)

@reg("Strong rally first: buy stop +0.43% above prior close, stop -0.65%, exit close", "misc.invest 1994: 'If the S&P rallys strongly first then use a buy stop at +200 points above yesterday's close and use a 300 point stop loss'", "i")
def f(D):
    _, _, pc = pdh(D); lv = pc * 1.0043; return single(D, np.isfinite(pc), 1, lv, stop=lv * (1 - .0065))

@reg("Weakness buy: first 90 min at/below prior close -> 0.43% trailing buy stop, stop -0.65%, exit close", "misc.invest 1994: 'For the first 1 1/2 hours, if the S&P trades at unchanged or lower than Friday's close, use a 200 point trailing buy stop ... 300 point stop'", "t")
def f(D):
    O, H, L, C = D["o"], D["h"], D["l"], D["c"]; pc = lag(D["dc"]); out = []
    for t in range(1, len(pc)):
        lo = 1e18; ent = None
        for m in range(90):
            if L[t, m] <= pc[t]: lo = min(lo, L[t, m])
            if lo < 1e17 and m > 0 and H[t, m] >= lo * 1.0043: ent = (m, max(lo * 1.0043, O[t, m])); break
        if ent is None: continue
        m, fp = ent; st = fp * (1 - .0065); x = C[t, -1]
        for k in range(m, 390):
            if L[t, k] <= st: x = st if k > m else min(st, fp); break
        out.append((t, 1, fp, x))
    return ("t", out)

@reg("RSI(14) <= 30 buy, >= 70 sell (stop-and-reverse)", "alt.invest.technical-analysis.omega 1990s: 'If (RSI <= 30) Then BUY elsif (RSI >= 70) Then SELL'", "d")
def f(D):
    c = D["dc"]; r = rsi(c, 14); u = nz(r <= 30); d = nz(r >= 70); return sig(state(u, d, d, u))

@reg("Range expansion: today's range > range 15 days ago -> long next day open->close", "misc.invest 1990s: 'a system that tells one to go long if the range in prices today is greater than that of 15 days ago'", "d")
def f(D):
    r = D["dh"] - D["dl"]; return ("d", lag((r > lag(r, 15)).astype(float)), "oc")


# ---------------------------------------------------------------- batch 3 (comp.ai.neural-nets, Japanese fj/japan.*, German de.*, uk.*)
@reg("Friday move > +1% -> long Friday close to Monday close; < -1% -> short", "comp.ai.neural-nets 1999: 'buy index if Friday return is >1% and sell short if <-1%, and exit Monday at close'", "t")
def f(D):
    d = D["days"]; c = D["dc"]; wd = d.weekday.values; r = c / lag(c) - 1; out = []
    for t in range(1, len(c) - 1):
        if wd[t] == 4 and wd[t + 1] == 0 and abs(r[t]) > .01: out.append((t, 1 if r[t] > 0 else -1, c[t], c[t + 1]))
    return ("t", out)

@reg("初押しは買い (first pullback is a buy): after a close at a 20-day high, first down close -> buy close, sell next close", "fj.soc.economy 1999 '怪しい話': 初押しは買いの鉄則通り (as the iron rule 'buy the first pullback')", "t")
def f(D):
    c = D["dc"]; hi = c >= hh(c, 20); out = []; armed = False
    for t in range(1, len(c) - 1):
        if hi[t]: armed = True; continue
        if armed and c[t] < c[t - 1]: out.append((t, 1, c[t], c[t + 1])); armed = False
    return ("t", out)

@reg("月末ドレッシング買い (month-end window dressing): buy close 3 days before month end, sell month-end close", "fj.soc.economy 1999: 月末のドレッシング買いを期待 (expecting month-end dressing buying)", "t")
def f(D):
    c = D["dc"]; me = np.nonzero(month_end(D))[0]; return ("t", [(k - 3, 1, c[k - 3], c[k]) for k in me if k >= 3])

@reg("German 4/9/18-day lines: long when 4 > 9 > 18, short when 4 < 9 < 18, else flat", "de.etc.finanz.boerse 1999: 'stieg gleich ueber die 4, 9 und 19 Tage Linie' (the classic 4-9-18 day lines)", "d")
def f(D):
    c = D["dc"]; a, b, e = sma(c, 4), sma(c, 9), sma(c, 18); return sig(np.where((a > b) & (b > e), 1, np.where((a < b) & (b < e), -1, 0)))

@reg("10-30 day oscillator: long when 10d SMA > 30d SMA, short below", "uk.finance.stockmarket 2000: 'If it has just passed the 10-30 day oscillator then there's a tenuous buy signal'", "d")
def f(D): c = D["dc"]; return sig(np.sign(sma(c, 10) - sma(c, 30)))


# ---------------------------------------------------------------- batch 4: 18th-century Japanese rice-market rules (酒田五法, Homma Munehisa,
# Dojima rice exchange, c. 1750). Daily candles; entry next open, exit after the stated holding unless noted.
def cndl(D):
    o, h, l, c = dly(D); body = c - o; rng = np.maximum(h - l, 1e-9); return o, h, l, c, body, rng

@reg("三空叩き込み (three gaps down -> buy): 3 consecutive down-gap opens -> buy next open, hold 3 days", "酒田五法 三空 (Homma, c.1750): 三空叩き込みに買い向かえ", "t")
def f(D):
    o, h, l, c, b, r = cndl(D); gd = o < lag(l); gu = o > lag(h); out = []
    for t in range(3, len(c) - 4):
        if nz(gd[t]) and nz(gd[t - 1]) and nz(gd[t - 2]): out.append((t + 1, 1, o[t + 1], c[t + 3]))
        if nz(gu[t]) and nz(gu[t - 1]) and nz(gu[t - 2]): out.append((t + 1, -1, o[t + 1], c[t + 3]))
    return ("t", out)

@reg("赤三兵/黒三兵 (three white soldiers buy / three black crows sell): 3 rising (falling) bullish (bearish) candles -> next open, hold 3 days", "酒田五法 三兵 (Homma, c.1750)", "t")
def f(D):
    o, h, l, c, b, r = cndl(D); out = []
    for t in range(3, len(c) - 4):
        ws = all(b[k] > 0 and c[k] > c[k - 1] and b[k] > .5 * r[k] for k in (t - 2, t - 1, t))
        bc = all(b[k] < 0 and c[k] < c[k - 1] and -b[k] > .5 * r[k] for k in (t - 2, t - 1, t))
        if ws: out.append((t + 1, 1, o[t + 1], c[t + 3]))
        elif bc: out.append((t + 1, -1, o[t + 1], c[t + 3]))
    return ("t", out)

@reg("三川明けの明星/宵の明星 (morning/evening star) -> next open, hold 3 days", "酒田五法 三川 (Homma, c.1750)", "t")
def f(D):
    o, h, l, c, b, r = cndl(D); out = []
    for t in range(3, len(c) - 4):
        a, m, z = t - 2, t - 1, t
        if b[a] < -.5 * r[a] and abs(b[m]) < .3 * r[m] and max(o[m], c[m]) < c[a] and b[z] > 0 and c[z] > (o[a] + c[a]) / 2: out.append((t + 1, 1, o[t + 1], c[t + 3]))
        if b[a] > .5 * r[a] and abs(b[m]) < .3 * r[m] and min(o[m], c[m]) > c[a] and b[z] < 0 and c[z] < (o[a] + c[a]) / 2: out.append((t + 1, -1, o[t + 1], c[t + 3]))
    return ("t", out)

@reg("包み線 (engulfing) at a 10-day extreme -> next open, hold 3 days", "Japanese candlestick tradition (Dojima, 18th c.); 抱き線", "t")
def f(D):
    o, h, l, c, b, r = cndl(D); lo10 = l <= ll(l, 10); hi10 = h >= hh(h, 10); out = []
    for t in range(10, len(c) - 4):
        if b[t] > 0 and b[t - 1] < 0 and c[t] > o[t - 1] and o[t] < c[t - 1] and (nz(lo10[t]) or nz(lo10[t - 1])): out.append((t + 1, 1, o[t + 1], c[t + 3]))
        if b[t] < 0 and b[t - 1] > 0 and c[t] < o[t - 1] and o[t] > c[t - 1] and (nz(hi10[t]) or nz(hi10[t - 1])): out.append((t + 1, -1, o[t + 1], c[t + 3]))
    return ("t", out)

@reg("Homma: 'when all are bearish, there is cause for prices to rise' -> after 5 straight down closes buy close, sell after 5 days (mirror short)", "本間宗久 宗久翁秘録 (c.1750): 万人が万人ながら弱気なれば、たわけになりて米を買うべし", "t")
def f(D):
    c = D["dc"]; dn = c < lag(c); up = c > lag(c); out = []
    for t in range(5, len(c) - 6):
        if all(nz(dn[t - k]) for k in range(5)): out.append((t, 1, c[t], c[t + 5]))
        elif all(nz(up[t - k]) for k in range(5)): out.append((t, -1, c[t], c[t + 5]))
    return ("t", out)


# ---------------------------------------------------------------- batch 5: old books (archive.org, 1870-1975)
@reg("Dow/Hamilton 'line': 15+ days inside a band < 4% wide, then a close beyond it -> follow, hold 20 days (time stop 3 days if no profit, Wyckoff)",
     "Nelson 1902 'ABC of stock speculation' / Hamilton 1922 'Stock market barometer': stays within a narrow range, say 2 points, until a long horizontal line forms; Wyckoff 1922: unless a stock shows a profit within two or three days, he closes the trade", "t")
def f(D):
    c = D["dc"]; hi = lag(hh(c, 15)); lo = lag(ll(c, 15)); narrow = (hi - lo) / c < .04; out = []; t = 15
    while t < len(c) - 21:
        if nz(narrow[t]) and (c[t] > hi[t] or c[t] < lo[t]):
            sd = 1 if c[t] > hi[t] else -1; x = t + 20
            if sd * (c[t + 3] - c[t]) <= 0: x = t + 3
            out.append((t, sd, c[t], c[x])); t = x + 1
        else: t += 1
    return ("t", out)


# ---------------------------------------------------------------- batch 6: non-price "weird" data claimed in the old literature / Usenet
EXT = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/oldweb/ext/"

def moon_age(days):
    """days since new moon (0 = new, ~14.77 = full), mean synodic month from the 2000-01-06 18:14 UTC new moon (+/- ~0.6 day)."""
    ref = pd.Timestamp("2000-01-06 18:14"); t = (days + pd.Timedelta(hours=16) - ref) / pd.Timedelta(days=1)   # 16:00 NY ~ 20:00-21:00 UTC
    return np.mod(t.values, 29.530588853)

def nyc_weather(D):
    import glob
    w = pd.concat([pd.read_csv(f, parse_dates=["DATE"]) for f in sorted(glob.glob(EXT + "nyc_*.csv"))]).drop_duplicates("DATE").set_index("DATE")
    return w.reindex(D["days"].normalize())

def kp_daily(D):
    k = pd.read_csv(EXT + "kp.txt", sep=r"\s+", comment="#", header=None, usecols=[0, 1, 2, 7], names=["y", "m", "d", "kp"])
    k = k[k.kp >= 0]; k["date"] = pd.to_datetime(dict(year=k.y, month=k.m, day=k.d)); return k.groupby("date").kp.max()

@reg("Lunar: long the 7 days around new moon, short the 7 days around full moon (open->open)", "misc.invest.futures 1998 'LUNAR ECLIPSE STOCK MARKET CRASH ALERT' & Dichev & Janes 2001 'Lunar cycle effects in stock returns'", "d")
def f(D):
    a = moon_age(D["days"]); h = np.where((a < 3.7) | (a > 25.8), 1, np.where(np.abs(a - 14.77) < 3.7, -1, 0)); return ("d", h.astype(float), "oo")

@reg("Full-moon short only: short open->close on the 3 trading days nearest full moon", "alt.astrology / misc.invest 1990s full-moon crash posts", "d")
def f(D):
    a = moon_age(D["days"]); return ("d", -(np.abs(a - 14.77) < 1.6).astype(float), "oc")

@reg("Wall Street weather: rain in Central Park -> short the day (open->close), dry -> long", "Saunders 1993 AER 'Stock prices and Wall Street weather' (Usenet-era classic); same-day rain, assumes the morning forecast", "d")
def f(D):
    w = nyc_weather(D); p = w.PRCP.values; return ("d", np.where(np.isnan(p), 0, np.where(p > 1.0, -1, 1)).astype(float), "oc")

@reg("Rain yesterday in NYC -> short next day open->close (causal version)", "Saunders 1993, lagged so it is fully known before the open", "d")
def f(D):
    w = nyc_weather(D); p = lag(w.PRCP.values); return ("d", np.where(np.isnan(p), 0, np.where(p > 1.0, -1, 0)).astype(float), "oc")

@reg("Geomagnetic storm (max Kp >= 5 on any of the prior 3 days) -> short next day open->close", "Krivelyova & Robotti 2003 'Playing the field: geomagnetic storms and the stock market' (Kp from GFZ Potsdam)", "d")
def f(D):
    k = kp_daily(D).reindex(D["days"].normalize()).values
    s = pd.Series(k).rolling(3, min_periods=1).max().shift(1).values; return ("d", -(np.nan_to_num(s) >= 5).astype(float), "oc")

@reg("Pre-holiday: long the last trading day before a US market holiday (open->close)", "Ariel 1990 J. Finance 'High stock returns before holidays' (cited on misc.invest)", "d")
def f(D):
    d = D["days"]; gap = np.r_[(d[1:] - d[:-1]).days, 1]; wd = d.weekday.values
    pre = ((gap > 1) & ~((wd == 4) & (gap == 3))) | ((wd == 4) & (gap > 3)) | ((wd < 4) & (gap > 1))
    return ("d", pre.astype(float), "oc")


# ---------------------------------------------------------------- batch 7: financial astrology (alt.astrology.moderated, Citystats 'Foresight Hindsight' 2000-01)
_ASP = None
def aspect_score(D, orb=1.0):
    """per RTH minute: (# soft Moon aspects 60/120) - (# hard Moon aspects 0/90/180) within orb degrees, Moon vs Sun..Neptune."""
    global _ASP
    if _ASP is not None: return _ASP
    import ephem
    days = D["days"]; t = (days.normalize().repeat(390) + pd.to_timedelta(np.tile(np.arange(390) + 570, len(days)), unit="m"))
    utc = t.tz_localize("America/New_York", ambiguous="NaT", nonexistent="shift_forward").tz_convert("UTC").tz_localize(None)
    L = ephem.longitudes(pd.DatetimeIndex(utc)); m = L.pop("moon"); sc = np.zeros(len(t))
    for p, lp in L.items():
        sep = np.abs(np.mod(m - lp + 180, 360) - 180)
        for a, w in ((0, -1), (90, -1), (180, -1), (60, 1), (120, 1)): sc += w * (np.abs(sep - a) < orb)
    _ASP = sc.reshape(len(days), 390); return _ASP

@reg("Astro intraday: first Moon aspect window of the session (9:35-15:00): soft -> long, hard -> short, exit when it ends",
     "alt.astrology.moderated 2000-01 'Citystats Foresight Hindsight': hard aspects drop the markets, soft aspects take them up", "t")
def f(D):
    S_ = aspect_score(D); O, C = D["o"], D["c"]; out = []
    for t in range(len(O)):
        s = S_[t]
        for m in range(5, 330):
            if s[m] != 0 and s[m - 1] == 0:
                sd = int(np.sign(s[m])); k = m + 1
                while k < 389 and np.sign(s[k]) == sd: k += 1
                out.append((t, sd, O[t, m + 1], O[t, min(k + 1, 389)] if k < 389 else C[t, -1])); break
    return ("t", out)

@reg("Astro daily: net soft-minus-hard Moon aspect minutes in the session > 0 -> long open->close, < 0 -> short",
     "alt.astrology.moderated 2000-01 'Citystats': the reason we have been down ... is the aspects; because the aspects have been harder, the market has been going down", "d")
def f(D):
    S_ = aspect_score(D); return ("d", np.sign(S_.sum(1)).astype(float), "oc")
