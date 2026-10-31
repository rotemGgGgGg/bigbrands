"""Stage 1 - theory generation. A theory is a complete entry idea written from parts every trader uses:
  ANCHOR  a time-based candle / session range / previous-day range / gap  (what defines the 0-1 of the Fib)
  LEVEL   a Fibonacci level of that range, oriented by side (long: low + x*range, short: high - x*range)
  TRIGGER limit touch (fade/retrace), stop break, 1-min close through, or sweep & reclaim (wick through, close back) = ICT style
  WINDOW  how long after the anchor completes the idea is valid
  SIDE    long or short
  CONTEXT a regime known at 04:00: previous-day direction, overnight drift to 04:00, previous-day volatility
Every theory is then tested with 60 exit plans (stop x target x time) in stage 2."""
import itertools

# anchors: (name, kind, a, b) with minute indexes from 04:00 (09:30 = 330). kind 'bar' = candle(s) from a to b inclusive.
def hm(s): h, m = map(int, s.split(":")); return (h - 4) * 60 + m
ANCHORS = []
for t in ("04:00", "05:00", "06:00", "07:00", "08:00", "08:30", "09:00", "09:15", "09:20", "09:23", "09:25", "09:28", "09:29",
          "09:30", "09:31", "09:32", "09:35", "09:45", "10:00", "10:30", "11:00", "12:00", "13:00", "13:30", "14:00", "14:30", "15:00"):
    ANCHORS.append((f"{t} 1m candle", "bar", hm(t), hm(t)))
for t in ("08:30", "09:30", "09:35", "09:45", "10:00", "10:30", "13:30", "14:00", "15:00"):
    ANCHORS.append((f"{t} 5m candle", "bar", hm(t), hm(t) + 4))
for t in ("08:30", "09:30", "09:45", "10:00", "14:00"):
    ANCHORS.append((f"{t} 15m candle", "bar", hm(t), hm(t) + 14))
for a, b in (("04:00", "09:29"), ("08:00", "09:29"), ("08:30", "09:29"), ("09:00", "09:29"), ("09:30", "09:44"), ("09:30", "09:59"),
             ("09:30", "10:29"), ("09:30", "10:59"), ("09:30", "11:59"), ("12:00", "13:29")):
    ANCHORS.append((f"{a}-{b} range", "bar", hm(a), hm(b)))
ANCHORS += [("previous RTH day", "pd", 0, 0), ("previous day first hour", "pdfh", 0, 0), ("previous day last hour", "pdlh", 0, 0),
            ("previous 2 days", "p2d", 0, 0), ("gap (prior close - open)", "gap", 0, 0)]
LEVELS = (-3.0, -2.618, -2.0, -1.618, -1.272, -1.0, -0.618, -0.5, -0.272, 0.0, 0.236, 0.382, 0.5, 0.618, 0.705, 0.786, 1.0,
          1.272, 1.618, 2.0, 2.618)
TRIGGERS = {"lim": "limit order resting at the level", "stp": "stop order through the level", "cls": "1-min close through the level",
            "rcl": "sweep beyond the level and close back (reclaim)"}
WINDOWS = (15, 60, 180, 9999)       # minutes after the anchor completes; 9999 = until 15:00
SIDES = (1, -1)
CONTEXT = list(itertools.product(("any", "with", "against"), ("any", "with", "against"), ("any", "calm", "wild")))
STOPS = (0.5, 1.0, 2.0, 4.0); TGTS = (0.5, 1.0, 2.0, 4.0, 8.0); HOLD = (30, 90, 9999)   # in range units / minutes after fill


def groups():
    return list(itertools.product(range(len(ANCHORS)), LEVELS, TRIGGERS, WINDOWS, SIDES))


def describe(ai, x, trg, w, sd, ctx=None):
    side = "LONG" if sd > 0 else "SHORT"; nm = ANCHORS[ai][0]
    where = f"Fib {x} of the {nm} ({'0 = low, 1 = high' if sd > 0 else '0 = high, 1 = low'})"
    win = "until 15:00" if w == 9999 else f"within {w} min after it completes"
    s = f"{side}: {TRIGGERS[trg]} at {where}, {win}"
    if ctx: s += f"; context prev-day={ctx[0]}, overnight={ctx[1]}, volatility={ctx[2]}"
    return s


if __name__ == "__main__":
    import csv, gzip, os
    G = groups(); n = len(G) * len(CONTEXT)
    print(f"anchors {len(ANCHORS)} x levels {len(LEVELS)} x triggers {len(TRIGGERS)} x windows {len(WINDOWS)} x sides 2 = {len(G):,} entry rules")
    print(f"x contexts {len(CONTEXT)} = {n:,} theories; x exit plans {len(STOPS) * len(TGTS) * len(HOLD)} = {n * 60:,} variants")
    out = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/mega_theories.csv.gz"
    with gzip.open(out, "wt", newline="") as f:
        w = csv.writer(f); w.writerow(["theory_id", "description"]); k = 0
        for g in G:
            for c in CONTEXT: w.writerow([k, describe(*g, ctx=c)]); k += 1
    print("written", out); print("example:", describe(*G[12345], ctx=CONTEXT[5]))
