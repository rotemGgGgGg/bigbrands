import os, lzma, struct, time, datetime as dt, concurrent.futures as cf, subprocess
days = [dt.date(2020,1,1) + dt.timedelta(d) for d in range((dt.date(2026,10,12) - dt.date(2020,1,1)).days)]
days = [d for d in days if d.weekday() < 5]
os.makedirs("raw", exist_ok=True)
def get(d):
    fn = f"raw/{d}.bi5"
    if os.path.exists(fn) and os.path.getsize(fn) > 0: return 1
    url = f"https://datafeed.dukascopy.com/datafeed/XAUUSD/{d.year}/{d.month-1:02d}/{d.day:02d}/BID_candles_min_1.bi5"
    for k in range(5):
        r = subprocess.run(["curl", "-sS", "--max-time", "40", "-o", fn, "-w", "%{http_code}", url], capture_output=True, text=True)
        if r.stdout == "200" and os.path.getsize(fn) > 0: return 1
        if r.stdout == "404": open(fn, "wb").close(); return 0
        time.sleep(2 * (k + 1))
    return -1
with cf.ThreadPoolExecutor(6) as ex:
    res = list(ex.map(get, days))
print("ok", res.count(1), "empty", res.count(0), "failed", res.count(-1))
