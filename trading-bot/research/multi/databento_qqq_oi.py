"""QQQ option open interest by strike and expiry, per day, from Databento OPRA (OPRA.PILLAR).
Used to rebuild "options heatmap" levels (heavy strikes, 0DTE put/call walls) and map them onto NQ.

Key from the environment variable DATABENTO_API_KEY (set it in your own terminal; never paste it into a chat).

    python multi/databento_qqq_oi.py 2024 2026         # prints the price only, downloads nothing
    python multi/databento_qqq_oi.py 2024 2026 --yes   # downloads month by month (resumable)

Output: $EDGE_DATA/opra/QQQ_OI_<YYYY-MM>.npz with arrays: day (YYYYMMDD), exp (YYYYMMDD), strike, cp (+1 call, -1 put), oi.
"""
import os, sys, io, csv, base64, ssl, time, datetime as dt, urllib.request, urllib.parse, urllib.error
import numpy as np

DATA = os.path.join(os.path.expanduser(os.environ.get("EDGE_DATA", "~/edge-data")), "")
OUT = DATA + "opra/"
API = "https://hist.databento.com/v0/"
BASE = dict(dataset="OPRA.PILLAR", symbols="QQQ.OPT", stype_in="parent")
CTX = ssl.create_default_context(cafile=os.environ.get("SSL_CERT_FILE") or None)


def call(endpoint, params, timeout=900):
    key = os.environ.get("DATABENTO_API_KEY")
    if not key: sys.exit("Set DATABENTO_API_KEY first (in this terminal):  set DATABENTO_API_KEY=db-...")
    req = urllib.request.Request(API + endpoint, data=urllib.parse.urlencode(params).encode(), method="POST", headers={
        "Authorization": "Basic " + base64.b64encode((key + ":").encode()).decode(), "User-Agent": "edge-lab-research/1.0"})
    for k in range(5):
        try:
            with urllib.request.urlopen(req, context=CTX, timeout=timeout) as r: return r.read()
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:300]
            if e.code in (400, 401, 402, 403, 422): sys.exit(f"Databento {e.code}: {body}")
            time.sleep(5 * (k + 1))
        except Exception as e:
            print("retry:", e, flush=True); time.sleep(5 * (k + 1))
    sys.exit("Databento did not answer after 5 tries.")


def months(y0, y1):
    d = dt.date(y0, 1, 1); end = min(dt.date(y1 + 1, 1, 1), dt.date.today())
    while d < end:
        n = dt.date(d.year + (d.month == 12), d.month % 12 + 1, 1)
        yield d, min(n, end); d = n


def ymd(ns):
    return int(dt.datetime.fromtimestamp(int(ns) / 1e9, dt.timezone.utc).strftime("%Y%m%d"))


def month(a, b):
    f = OUT + f"QQQ_OI_{a:%Y-%m}.npz"
    if os.path.exists(f) and b <= dt.date.today().replace(day=1): return
    span = dict(start=a.isoformat(), end=b.isoformat())
    defs = {}
    raw = call("timeseries.get_range", {**BASE, **span, "schema": "definition", "encoding": "csv", "pretty_px": "true",
                                         "pretty_ts": "false", "map_symbols": "false", "compression": "none"})
    for r in csv.DictReader(io.StringIO(raw.decode())):
        try: defs[r["instrument_id"]] = (ymd(r["expiration"]), float(r["strike_price"]), 1 if r["instrument_class"] == "C" else -1)
        except (ValueError, KeyError): pass
    raw = call("timeseries.get_range", {**BASE, **span, "schema": "statistics", "encoding": "csv", "pretty_px": "true",
                                         "pretty_ts": "false", "map_symbols": "false", "compression": "none"})
    rows = []
    for r in csv.DictReader(io.StringIO(raw.decode())):
        if r.get("stat_type") != "9" or r["instrument_id"] not in defs: continue      # 9 = open interest
        e, k, cp = defs[r["instrument_id"]]
        rows.append((ymd(r["ts_event"]), e, k, cp, float(r["quantity"])))
    a_ = np.array(rows, float).reshape(-1, 5)
    np.savez_compressed(f, day=a_[:, 0].astype(int), exp=a_[:, 1].astype(int), strike=a_[:, 2], cp=a_[:, 3].astype(int), oi=a_[:, 4])
    print(f"{a:%Y-%m}: {len(a_):,} open-interest rows, {len(defs):,} contracts", flush=True)


if __name__ == "__main__":
    y0, y1 = int(sys.argv[1]), int(sys.argv[2]); os.makedirs(OUT, exist_ok=True)
    if "--yes" not in sys.argv:
        total = 0.0
        for y in range(y0, y1 + 1):
            span = dict(start=f"{y}-01-01", end=min(dt.date(y + 1, 1, 1), dt.date.today()).isoformat())
            c = sum(float(call("metadata.get_cost", {**BASE, **span, "schema": s}, timeout=180)) for s in ("definition", "statistics"))
            total += c; print(f"{y}: ${c:.2f}", flush=True)
        print(f"TOTAL: ${total:.2f}  (charged to your Databento credits). Run again with --yes to download.")
        sys.exit(0)
    for a, b in months(y0, y1): month(a, b)
    print("done ->", OUT)
