"""Stage 1c - the weird corners: astrology, gambling-system, genetic-algorithm, statistics/prediction and craps/lottery groups,
keeping only posts (<= 2002) that talk about the stock market / index futures."""
import os, re, json, time
import harvest as H, mine
GROUPS = {"usenet-alt": ["alt.astrology", "alt.astrology.moderated", "alt.astrology.pro", "alt.gambling", "alt.sci.math.statistics.prediction"],
          "usenet-comp": ["comp.ai.genetic"], "usenet-rec": ["rec.gambling", "rec.gambling.misc"], "usenet-sci": ["sci.stat.math"]}
MKT = re.compile(r"stock market|dow jones|\bdjia\b|s&p|nasdaq|index futures|\bthe dow\b|wall street|stock index|e-?mini", re.I)
_score = mine.score
def score(t):
    s, c = _score(t)
    return (s if MKT.search(t) else 0), c
mine.score = score

if __name__ == "__main__":
    for col, gs in GROUPS.items():
        for g in gs:
            res = H.SP + f"mined/{g}.jsonl"
            if os.path.exists(res): continue
            z = H.SP + f"raw/{g}.zip"; t0 = time.time()
            if not H.fetch(col, g, z): print("FAILED", g, flush=True); continue
            st = mine.mine_zip(z, res, g); os.remove(z); print(g, json.dumps(st), f"{time.time() - t0:.0f}s", flush=True)
    print("weird harvest done", flush=True)
