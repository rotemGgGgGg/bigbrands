"""Search space of the ICT engine and random sampling. Every dimension is a published interpretation (Silver Bullet windows,
macro 09:50-10:10, London killzone, ORB/IB ranges, TJR/ICT sweep → MSS/CISD → FVG/IFVG chains, ICT-bot flat 1.1 RR, ...)."""
import numpy as np
import ict_engine as E
from ict_data import t2m

COST_PTS = 0.75     # MNQ commission + exchange/NFA ≈ $1.50 round trip = 0.75 NQ points
SLIP_PTS = 0.25     # 1 tick on every market-type fill (market entry, stop exit, time exit)
WINDOWS = [("09:30", "10:00"), ("09:30", "10:30"), ("09:30", "11:00"), ("09:30", "12:00"), ("09:50", "10:10"), ("10:00", "11:00"),
           ("13:30", "14:30"), ("14:00", "15:00"), ("02:00", "05:00"), ("08:30", "11:00"), ("09:00", "10:00"), ("09:45", "11:30")]
CHOICES = dict(texit=("we+30", "we+90", "15:55"), rolln=(15, 30, 60, 120), sweep=(0, 1), conf=(0, 1, 2, 3), confn=(5, 15, 30, 60),
               disp=(0.0, 0.5, 1.0, 1.5, 2.0), pivk=(2, 3, 5), entry=(0, 1, 2, 3, 4), valid=(5, 15, 30, 60), stopm=(0, 1, 2),
               sbuf=(0.0, 0.5, 2.0, 5.0), satr=(1.0, 2.0, 3.0, 5.0), tpm=(0, 1), tpr=(1.0, 1.1, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0),
               ber=(0.0, 1.0, 1.5, 2.0), bias=(0, 1, 2, 3, 4), side=(0, 1, -1), maxt=(1, 2, 3), minr=(1.0, 3.0, 6.0),
               maxr=(20.0, 40.0, 80.0, 1e9), sal=(0, 1))


def texit_min(code, we):
    if code == "we+30": return min(we + 30, t2m("15:55"))
    if code == "we+90": return min(we + 90, t2m("15:55"))
    return t2m("15:55")


def make(w, mask, cx=1.0, **kw):
    P = np.zeros(E.NPAR); ws, we = t2m(WINDOWS[w][0]), t2m(WINDOWS[w][1])
    P[E.WS], P[E.WE], P[E.LMASK] = ws, we, mask
    P[E.ROLLN], P[E.SWEEP], P[E.CONF], P[E.CONFN], P[E.DISP], P[E.PIVK] = kw["rolln"], kw["sweep"], kw["conf"], kw["confn"], kw["disp"], kw["pivk"]
    P[E.ENTRY], P[E.VALID], P[E.STOPM], P[E.SBUF], P[E.SATR] = kw["entry"], kw["valid"], kw["stopm"], kw["sbuf"], kw["satr"]
    P[E.TPM], P[E.TPR], P[E.BER], P[E.TEXIT], P[E.BIAS], P[E.SIDE] = kw["tpm"], kw["tpr"], kw["ber"], texit_min(kw["texit"], we), kw["bias"], kw["side"]
    P[E.MAXT], P[E.MINR], P[E.MAXR], P[E.SAL] = kw["maxt"], kw["minr"], kw["maxr"], kw["sal"]
    P[E.THRU], P[E.COST], P[E.SLIP] = 0.25, COST_PTS * cx, SLIP_PTS * cx
    return P


def sample(rng, cx=1.0, return_dict=False):
    w = int(rng.integers(len(WINDOWS)))
    nb = int(rng.integers(1, 4)); mask = 0
    for b in rng.choice(9, nb, replace=False): mask |= 1 << int(b)
    kw = {k: v[int(rng.integers(len(v)))] for k, v in CHOICES.items()}
    P = make(w, mask, cx, **kw)
    if return_dict: return P, dict(w=w, mask=mask, **kw)
    return P
