"""Stage 3 - pull explicit conditional trading rules out of every mined post: sentences of the form 'if/when/after <condition>
... buy/sell/long/short' (or the reverse order), plus Japanese/Chinese/German equivalents, and statistic claims
('x% of the time', 'n out of m', 勝率). Exact duplicates are merged and counted (a rule repeated by many posters ranks higher)."""
import json, re, glob, collections, sys
import mine, snippets
SP = snippets.SP
COND = re.compile(
    r"\b(if|when|whenever|after|once|on days?|each time)\b[^.?!]{3,160}\b(buy|sell|go long|go short|long|short|enter|fade)\b|"
    r"\b(buy|sell|go long|go short|enter|fade)\b[^.?!]{0,80}\b(if|when|whenever|after|on the (?:open|close)|at the (?:open|close)|on a stop|"
    r"on (?:monday|tuesday|wednesday|thursday|friday)s?)\b|"
    r"(たら|れば|なら|ときは|時は)[^。]{0,60}(買|売|ドテン)|(買|売)[^。]{0,40}(たら|れば|なら)|"
    r"(如果|若|當|当)[^。]{0,60}(買|賣|做多|做空)|"
    r"\b(wenn|falls)\b[^.]{0,120}\b(kaufen|verkaufen|long|short)\b", re.I)
SPAM = re.compile(r"http|www\.|\$\d{3,}|newsletter|free trial|subscribe|e-?mail|call now|guarantee|profit(?:s)? of \$", re.I)


def norm(s): return re.sub(r"[\d.,/$%-]+", "#", s.lower())


if __name__ == "__main__":
    cnt = collections.Counter(); ex = {}; src = collections.defaultdict(set)
    for f in sorted(glob.glob(SP + "mined/*.jsonl")):
        for ln in open(f):
            x = json.loads(ln)
            for s in snippets.SPLIT.split(x["text"]):
                s = " ".join(s.split())
                if not (30 <= len(s) <= 400) or SPAM.search(s): continue
                if not (COND.search(s) or snippets.STAT.search(s)): continue
                if not mine.RX["hook"].search(s): continue
                k = norm(s)[:160]; cnt[k] += 1; src[k].add(x["g"])
                if k not in ex: ex[k] = (x["y"], x["g"], s)
    rows = sorted(ex, key=lambda k: (-cnt[k], k))
    with open(SP + "rule_sentences.tsv", "w") as fo:
        for k in rows:
            y, g, s = ex[k]; fo.write(f"{cnt[k]}\t{y}\t{g}\t{s}\n")
    print(len(rows), "distinct rule sentences")
