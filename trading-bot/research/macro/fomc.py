"""FOMC statement days (2:00 pm ET decision day = last day of scheduled meetings), from federalreserve.gov pages saved in the scratchpad."""
import re, pandas as pd
D = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/macro/"
MO = {m: i + 1 for i, m in enumerate("January February March April May June July August September October November December".split())}
MS = {m[:3]: v for m, v in MO.items()}
def dates():
    out = set()
    for y in range(2011, 2021):
        t = open(D + f"f{y}.htm", encoding="utf8", errors="ignore").read()
        for mo, d1, d2, yy in re.findall(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d+)(?:-(\d+))?\s+Meeting\s+-\s+(\d{4})", t):
            out.add(pd.Timestamp(int(yy), MO[mo], int(d2 or d1)))
        # cross-month meetings e.g. "October 31-November 1 Meeting"
        for m1, d1, m2, d2, yy in re.findall(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d+)-(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d+)\s+Meeting\s+-\s+(\d{4})", t):
            out.add(pd.Timestamp(int(yy), MO[m2], int(d2)))
        for m1, m2, d1, d2, yy in re.findall(r"([A-Z][a-z]{2})/([A-Z][a-z]{2})\s+(\d+)-(\d+)\s+Meeting\s+-\s+(\d{4})", t):
            out.add(pd.Timestamp(int(yy), MS[m2], int(d2)))
    t = open(D + "fomc_cur.htm", encoding="utf8", errors="ignore").read()
    for sec in re.split(r'<h4><a id="\d+">', t)[1:]:
        yy = int(sec[:4])
        for mo, dt in re.findall(r'fomc-meeting__month[^>]*>(?:<strong>)?([^<]+)<.*?fomc-meeting__date[^>]*>([^<]+)<', sec, re.S):
            if "notation" in dt or "unscheduled" in dt.lower(): continue
            ds = re.findall(r"\d+", dt); mos = mo.strip().split("/")
            if not ds: continue
            mm = MO.get(mos[-1].strip()) or MS.get(mos[-1].strip()[:3]); out.add(pd.Timestamp(yy, mm, int(ds[-1])))
    return sorted(d for d in out if pd.Timestamp(2012, 1, 1) <= d <= pd.Timestamp(2026, 11, 10))
if __name__ == "__main__":
    d = dates(); s = pd.Series(1, index=pd.DatetimeIndex(d)); print(len(d)); print(s.groupby(s.index.year).size().to_dict()); print(d[-10:])
