"""Free 1-minute BID candles from Dukascopy's public datafeed (daily LZMA .bi5 files, UTC), 2012 - 2026-10.
Saved per instrument as scratchpad/duka/<SYM>.npz: t (UTC epoch minutes), o, h, l, c (price), v. No packages; resumable."""
import os, sys, lzma, struct, subprocess, time, datetime as dt
import numpy as np
from concurrent.futures import ThreadPoolExecutor
OUT = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/duka/"
SYMS = {  # name: price divisor
    "DEUIDXEUR": 1e3, "GBRIDXGBP": 1e3, "JPNIDXJPY": 1e3, "USA500IDXUSD": 1e3, "USATECHIDXUSD": 1e3, "USA30IDXUSD": 1e3, "EUSIDXEUR": 1e3,
    "FRAIDXEUR": 1e3, "AUSIDXAUD": 1e3, "HKGIDXHKD": 1e3, "XAUUSD": 1e3, "XAGUSD": 1e3, "LIGHTCMDUSD": 1e3, "BRENTCMDUSD": 1e3,
    "EURUSD": 1e5, "USDJPY": 1e3, "GBPUSD": 1e5, "AUDUSD": 1e5, "USDCAD": 1e5, "EURJPY": 1e3}


import http.client, ssl, threading, urllib.parse
_TL = threading.local(); _PR = urllib.parse.urlparse(os.environ["HTTPS_PROXY"]); _CTX = ssl.create_default_context(cafile="/root/.ccr/ca-bundle.crt")


def _conn(new=False):
    if new or not hasattr(_TL, "c"):
        if hasattr(_TL, "c"):
            try: _TL.c.close()
            except Exception: pass
        _TL.c = http.client.HTTPSConnection(_PR.hostname, _PR.port, context=_CTX, timeout=30); _TL.c.set_tunnel("datafeed.dukascopy.com", 443)
    return _TL.c


def day(sym, d):
    path = f"/datafeed/{sym}/{d.year}/{d.month - 1:02d}/{d.day:02d}/BID_candles_min_1.bi5"
    for k in range(6):
        try:
            c = _conn(k > 0); c.request("GET", path, headers={"User-Agent": "Mozilla/5.0"}); r = c.getresponse(); body = r.read()
        except Exception:
            time.sleep(1 + k); continue
        if r.status == 404 or (r.status == 200 and not body): return None
        if r.status != 200: time.sleep(1 + k); continue
        try: b = lzma.decompress(body)
        except Exception: return None
        a = np.frombuffer(b, dtype=">i4").reshape(-1, 6)
        base = int(dt.datetime(d.year, d.month, d.day, tzinfo=dt.timezone.utc).timestamp() // 60)
        return np.c_[base + a[:, 0] // 60, a[:, 1:5], np.frombuffer(b, dtype=">f4").reshape(-1, 6)[:, 5]]
    return "ERR"


def get(sym, y0=2012, y1=2026, threads=6):
    """year by year into OUT/<sym>_<year>.npy (resumable), then merged into OUT/<sym>.npz."""
    f = OUT + sym + ".npz"
    if os.path.exists(f): return sym, "cached"
    errs = 0
    for y in range(y0, y1 + 1):
        fy = OUT + f"{sym}_{y}.npy"
        if os.path.exists(fy): continue
        end = dt.date(y, 12, 31) if y < 2026 else dt.date(2026, 10, 31)
        ds = [dt.date(y, 1, 1) + dt.timedelta(n) for n in range((end - dt.date(y, 1, 1)).days + 1)]; ds = [d for d in ds if d.weekday() != 5]
        with ThreadPoolExecutor(threads) as ex: res = list(ex.map(lambda d: day(sym, d), ds))
        e = sum(1 for r in res if isinstance(r, str)); errs += e; rows = [r for r in res if r is not None and not isinstance(r, str)]
        np.save(fy, np.concatenate(rows) if rows else np.zeros((0, 6))); print(sym, y, len(rows), "days, errors", e, flush=True)
    parts = [np.load(OUT + f"{sym}_{y}.npy") for y in range(y0, y1 + 1)]; a = np.concatenate([p for p in parts if len(p)])
    if not len(a): return sym, "no data"
    dv = SYMS[sym]; np.savez_compressed(f, t=a[:, 0].astype(np.int64), o=a[:, 1] / dv, h=a[:, 4] / dv, l=a[:, 3] / dv, c=a[:, 2] / dv, v=a[:, 5])
    return sym, f"{len(a):,} bars, errors {errs}"


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for s in (sys.argv[1:] or SYMS):
        t0 = time.time(); print(*get(s), f"{time.time() - t0:.0f}s", flush=True)
    print("duka done", flush=True)
