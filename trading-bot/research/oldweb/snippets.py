"""Stage 3 helper - cut each mined post down to its rule-like sentences (action + timing hook + number in the same sentence,
or a statistic like 'x% of the time' / 'since 19xx'), so thousands of posts can be read as short snippets."""
import json, re, glob, sys, hashlib
import mine
SP = mine.__file__ and "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/oldweb/"
STAT = re.compile(r"\d+(?:\.\d+)?\s*%\s*of the time|\d+ out of (?:the last )?\d+|since 19\d\d|win(?:ning)? (?:rate|percentage)|"
                  r"profit factor|勝率|\d+勝\d+敗|\d+回中\d+回|trefferquote", re.I)
SPLIT = re.compile(r"(?<=[.!?。！？])\s+|\n\s*\n")


def snips(t):
    out = []
    for s in SPLIT.split(t):
        s = " ".join(s.split())
        if not (25 <= len(s) <= 600): continue
        a, h, n = (bool(mine.RX[k].search(s)) for k in ("act", "hook", "num"))
        st = bool(STAT.search(s))
        if (a and h and n) or (st and (a or h)): out.append((2 * st + a + h + n, s))
    out.sort(key=lambda x: -x[0]); return [s for _, s in out[:4]]


if __name__ == "__main__":
    seen = set(); rows = []
    for f in sorted(glob.glob(SP + "mined/*.jsonl")):
        for ln in open(f):
            x = json.loads(ln); ss = snips(x["text"])
            if not ss: continue
            k = hashlib.md5(ss[0].lower().encode()).hexdigest()
            if k in seen: continue
            seen.add(k); rows.append(dict(g=x["g"], y=x["y"], subj=x["subj"][:90], s=ss, score=x["score"] + 3 * len(ss)))
    rows.sort(key=lambda r: -r["score"])
    with open(SP + "snippets.jsonl", "w") as fo:
        for r in rows: fo.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(len(rows), "posts with rule-like sentences")
