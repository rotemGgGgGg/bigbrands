"""Stage 1b - older than Usenet: (a) every textfiles.com directory (1980s-early-90s BBS files), keeping files whose name or
index description mentions markets; (b) open-access (not lending-library) books on archive.org dated 1880-1975 about
speculation, stock/commodity trading, price cycles and forecasting; (c) Japanese market books (相場 / 米相場 / 酒田 / 罫線).
Plain text is saved under scratchpad/oldweb/old/; nothing is executed."""
import os, re, json, subprocess, urllib.parse, time
SP = "/tmp/claude-0/-home-user-bigbrands/e3584704-f927-5cd0-bdfb-3c26d638e529/scratchpad/oldweb/old/"
KEY = re.compile(r"stock|market|invest|trad|commod|futur|wall ?st|money|financ|dow|gold|silver|forecast|cycle|astro|gann|elliott|"
                 r"chart|price|specul|option|bond|econom|rich|wealth", re.I)


def get(url, out=None, t=120):
    a = ["curl", "-gsSL", "-m", str(t), url] + (["-o", out] if out else [])
    for k in range(3):
        r = subprocess.run(a, capture_output=True)
        if r.returncode == 0: return r.stdout if out is None else True
        time.sleep(2 * (k + 1))
    return b"" if out is None else False


def textfiles():
    os.makedirs(SP + "tf", exist_ok=True); top = get("http://www.textfiles.com/directory.html").decode("latin-1")
    dirs = [d for d in re.findall(r'HREF="([a-z0-9]+)"', top, re.I)]; seen = set(); queue = [d + "/" for d in dirs]; n = 0
    while queue:
        d = queue.pop()
        if d in seen or d.count("/") > 4: continue
        seen.add(d); page = get("http://www.textfiles.com/" + d).decode("latin-1", "replace")
        for href, rest in re.findall(r'<A HREF="([^"]+)">[^<]*</A>\s*</B>?</?T?D?[^\n]*?(?:<TD[^>]*>)?([^\n<]*)', page, re.I) or []:
            pass
        for m in re.finditer(r'<A HREF="([^"?#:]+)">([^<]*)</A>(.{0,400}?)(?=<A HREF|$)', page, re.I | re.S):
            href, label, desc = m.group(1), m.group(2), re.sub(r"<[^>]+>", " ", m.group(3))
            if href.endswith("/"):
                if not href.startswith(("/", "..")): queue.append(d + href)
                continue
            if href.startswith(("/", "..", "http")) or href.endswith((".html", ".htm", ".gif", ".jpg", ".zip", ".exe")): continue
            if KEY.search(href) or KEY.search(label) or KEY.search(desc):
                out = SP + "tf/" + (d + href).replace("/", "__")
                if not os.path.exists(out) and get("http://www.textfiles.com/" + d + href, out, 60): n += 1
    return n


def books(query, tag, maxn=200):
    os.makedirs(SP + tag, exist_ok=True)
    q = urllib.parse.quote(query, safe="")
    url = f"https://archive.org/advancedsearch.php?q={q}&fl[]=identifier&fl[]=title&fl[]=year&rows={maxn}&output=json&sort[]=downloads+desc"
    try: docs = json.loads(get(url))["response"]["docs"]
    except Exception: return 0
    n = 0
    for x in docs:
        i = x["identifier"]; out = SP + f"{tag}/{i}.txt"
        if os.path.exists(out): continue
        loc = subprocess.run(["curl", "-sS", "-m", "60", "-o", "/dev/null", "-w", "%{redirect_url}", f"https://archive.org/download/{i}/{i}_djvu.txt"],
                             capture_output=True, text=True).stdout.strip()
        if not loc: continue
        if get(loc, out, 300) and os.path.getsize(out) > 5000 and b"<html" not in open(out, "rb").read(300).lower():
            open(out + ".meta", "w").write(json.dumps(x)); n += 1
        elif os.path.exists(out): os.remove(out)
    return n


if __name__ == "__main__":
    EN = ("mediatype:texts AND year:[1850 TO 1975] AND NOT collection:inlibrary AND NOT collection:printdisabled AND "
          "(subject:(speculation) OR subject:(stock exchange) OR subject:(stocks) OR subject:(commodity exchanges) OR subject:(futures) OR "
          "subject:(stock price forecasting) OR subject:(business cycles) OR subject:(investments) OR title:(speculation) OR title:(stock market) "
          "OR title:(wall street) OR title:(tape reading) OR title:(trading) OR title:(cycles) OR title:(forecasting))")
    print("books_en", books(EN, "books_en", 300), flush=True)
    JA = "mediatype:texts AND (相場 OR 米相場 OR 酒田 OR 罫線 OR 株式相場 OR 投機 OR 先物)"
    print("books_ja", books(JA, "books_ja", 150), flush=True)
    print("textfiles", textfiles(), flush=True)
    print("old harvest done", flush=True)
