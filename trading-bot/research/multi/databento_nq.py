"""NQ 1-minute OHLCV with real CME volume from Databento (GLBX.MDP3, front month by volume: NQ.v.0).

No packages: plain HTTPS to Databento's historical API. The key is read from the environment variable DATABENTO_API_KEY
(set it in your own terminal; never paste it into a chat or commit it).

    python multi/databento_nq.py            # prints the price of the whole download, downloads nothing
    python multi/databento_nq.py --yes      # downloads year by year (resumable) and builds the .npz

Output: $EDGE_DATA/databento/NQ_<year>.npy (t, o, h, l, c, v, rows) and $EDGE_DATA/databento/NQ.npz
t = UTC epoch minutes of the bar open; prices in index points; v = contracts.
"""
import os, sys, io, csv, json, base64, ssl, time, datetime as dt, urllib.request, urllib.parse, urllib.error
import numpy as np

DATA = os.path.join(os.path.expanduser(os.environ.get("EDGE_DATA", "~/edge-data")), "")
OUT = DATA + "databento/"
API = "https://hist.databento.com/v0/"
Q = dict(dataset="GLBX.MDP3", symbols="NQ.v.0", stype_in="continuous", schema="ohlcv-1m")
FIRST, CTX = 2011, ssl.create_default_context(cafile=os.environ.get("SSL_CERT_FILE") or None)


def call(endpoint, params, timeout=600):
    key = os.environ.get("DATABENTO_API_KEY")
    if not key: sys.exit("Set DATABENTO_API_KEY first (in this terminal):  set DATABENTO_API_KEY=db-...   (Windows cmd)")
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


def span(y):
    end = min(dt.date(y + 1, 1, 1), dt.date.today())
    return dict(start=f"{y}-01-01", end=end.isoformat())


def cost(y):
    return float(call("metadata.get_cost", {**Q, **span(y)}, timeout=120))


def fetch(y):
    f = OUT + f"NQ_{y}.npy"
    if os.path.exists(f) and y < dt.date.today().year: return np.load(f)
    raw = call("timeseries.get_range", {**Q, **span(y), "encoding": "csv", "pretty_px": "true", "pretty_ts": "false",
                                         "map_symbols": "false", "compression": "none"})
    rows = []
    for r in csv.DictReader(io.StringIO(raw.decode())):
        rows.append((int(r["ts_event"]) // 60_000_000_000, float(r["open"]), float(r["high"]), float(r["low"]),
                     float(r["close"]), float(r["volume"])))
    a = np.array(rows, float).reshape(-1, 6); np.save(f, a)
    print(y, f"{len(a):,} bars", flush=True)
    return a


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    years = list(range(FIRST, dt.date.today().year + 1))
    if "--yes" not in sys.argv:
        total = 0.0
        for y in years:
            c = cost(y); total += c; print(f"{y}: ${c:.2f}", flush=True)
        print(f"TOTAL: ${total:.2f}  (charged to your Databento credits). Run again with --yes to download.")
        sys.exit(0)
    a = np.concatenate([fetch(y) for y in years])
    a = a[np.argsort(a[:, 0], kind="stable")]; a = a[np.r_[True, np.diff(a[:, 0]) > 0]]
    np.savez_compressed(OUT + "NQ.npz", t=a[:, 0].astype(np.int64), o=a[:, 1], h=a[:, 2], l=a[:, 3], c=a[:, 4], v=a[:, 5])
    print(f"done: {len(a):,} bars -> {OUT}NQ.npz")
