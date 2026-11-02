"""Stage 2b - rule sentences from the old books / BBS files (same conditional + statistic filters as for Usenet)."""
import glob, json, os, re, collections, sys
import mine, snippets, rulesent
OLD = snippets.SP + "old/"


def sents(t):
    t = re.sub(r"-\n(\w)", r"\1", t); t = re.sub(r"\s*\n\s*", " ", t)
    for s in re.split(r"(?<=[.!?。])\s+", t):
        s = " ".join(s.split())
        if 40 <= len(s) <= 450: yield s


if __name__ == "__main__":
    rows = []; seen = set()
    for f in sorted(glob.glob(OLD + "*/*.txt")) + sorted(glob.glob(OLD + "tf/*")):
        meta = {}
        if os.path.exists(f + ".meta"): meta = json.load(open(f + ".meta"))
        src = f.split("/old/")[1]; title = meta.get("title", src)[:70]; yr = meta.get("year", "")
        try: t = open(f, errors="replace").read()
        except Exception: continue
        for s in sents(t):
            if not (rulesent.COND.search(s) or snippets.STAT.search(s)): continue
            if not mine.RX["hook"].search(s) or not mine.RX["num"].search(s + " 1 day"): continue
            k = rulesent.norm(s)[:120]
            if k in seen: continue
            seen.add(k); rows.append((yr, title, s))
    with open(snippets.SP + "old_rule_sentences.tsv", "w") as fo:
        for r in rows: fo.write("\t".join(map(str, r)) + "\n")
    print(len(rows), "rule sentences from", len(glob.glob(OLD + "*/*.txt")), "books +", len(glob.glob(OLD + "tf/*")), "BBS files")
