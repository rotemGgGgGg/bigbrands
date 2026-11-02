"""Stage 2 - mine each post (dated <= 2002) for a concrete, testable trading rule. A post scores when it states an action
(buy/sell/long/short, in EN/JA/ZH/DE), a market-timing hook (open, close, gap, weekday, month end, holiday, moon, moving average,
range, first hour...) and a number; quoted lines and signatures are dropped first. Output: one JSON line per candidate post."""
import zipfile, re, json, hashlib, email, email.policy, io
from email.header import decode_header, make_header

ACT = r"buy|sell|go long|go short|short it|long at|enter|exit|stop[- ]?loss|stop at|target|take profit|fade|" \
      r"買い|売り|買う|売る|仕掛け|手仕舞|損切|利食|ドテン|" r"買進|賣出|買入|賣|做多|做空|停損|停利|" \
      r"kaufen|verkaufen|einstieg|ausstieg|stopp|long gehen|short gehen"
HOOK = r"open(?:ing)?|clos(?:e|ing)|gap|monday|tuesday|wednesday|thursday|friday|weekday|month[- ]end|end of (?:the )?month|" \
       r"first (?:trading )?day|last (?:trading )?day|holiday|expiration|triple witching|full moon|new moon|lunar|eclipse|" \
       r"moving average|\bma\b|range|first hour|last hour|first \d+ minutes|high of the day|low of the day|inside day|outside day|" \
       r"narrow range|nr4|nr7|breakout|pivot|channel|oscillator|rsi|stochastic|williams|bollinger|volatility|vix|trin|tick|" \
       r"advance.?decline|put.?call|seasonal|january|september|october|december|time of day|lunch|noon|overnight|" \
       r"寄り付き|寄付|大引け|引け|前場|後場|窓|移動平均|陽線|陰線|十字|曜日|月曜|金曜|月末|満月|新月|新値|酒田|一目|ローソク|" \
       r"開盤|收盤|跳空|均線|週一|週五|月底|" r"eröffnung|schluss|montag|freitag|monatsende|vollmond|gleitende"
NUM = r"\d+(?:\.\d+)?\s*(?:%|points?|pts|ticks?|days?|bars?|minutes?|min|ポイント|円|銭|日|点|點|分)"
MARKET = r"s&p|sp500|spx|\bsp\b|nasdaq|ndx|nq|dow|djia|index|futures|e-?mini|nikkei|topix|日経|先物|指数|指數|期貨|台指|加權|dax|ftse|stocks?"
SYS = r"system|mechanical|rule|backtest|back-test|tested|test(?:ed)? it|win(?:ning)? (?:rate|percentage)|profit factor|drawdown|" \
      r"\d+% of the time|out of \d+|システム|勝率|検証|法則|アノマリー|規則|勝率|回測|系統|regel|getestet|trefferquote"
RX = {k: re.compile(v, re.I) for k, v in dict(act=ACT, hook=HOOK, num=NUM, mkt=MARKET, sys=SYS).items()}


def hdr(m, k):
    try: return str(make_header(decode_header(m.get(k, "") or "")))
    except Exception: return str(m.get(k, ""))


def body(m):
    try:
        part = next((p for p in m.walk() if p.get_content_type() == "text/plain"), None) if m.is_multipart() else m
        if part is None: return ""
        raw = part.get_payload(decode=True) or b""
        cs = part.get_content_charset() or ("iso-2022-jp" if b"\x1b$B" in raw else "latin-1")
        try: return raw.decode(cs, "replace")
        except LookupError: return raw.decode("latin-1", "replace")
    except Exception: return ""


def clean(t):
    out = []
    for ln in t.splitlines():
        s = ln.strip()
        if s.startswith((">", "|", ":", "＞")) or re.match(r"^(in article|.{0,60}wrote:|.{0,60}writes:)", s, re.I): continue
        if s in ("--", "-- "): break
        out.append(ln)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


def score(t):
    c = {k: len(r.findall(t)) for k, r in RX.items()}
    if not (c["act"] and c["hook"] and c["num"]): return 0, c
    return min(c["act"], 6) + min(c["hook"], 8) * 1.5 + min(c["num"], 6) + min(c["mkt"], 4) + min(c["sys"], 4) * 2, c


def messages(zf):
    with zipfile.ZipFile(zf) as z:
        for n in z.namelist():
            buf = []
            with z.open(n) as f:
                for line in io.BufferedReader(f):
                    if line.startswith(b"From ") and buf:
                        yield b"".join(buf); buf = []
                    buf.append(line)
            if buf: yield b"".join(buf)


def mine_zip(zf, out, grp):
    seen = set(); st = dict(posts=0, le2002=0, kept=0)
    with open(out, "w") as fo:
        for raw in messages(zf):
            st["posts"] += 1
            try: m = email.message_from_bytes(raw, policy=email.policy.compat32)
            except Exception: continue
            try: y = email.utils.parsedate_to_datetime(m.get("Date", "")).year
            except Exception:
                yy = re.search(r"\b(19[89]\d|20[0-2]\d)\b", str(m.get("Date", ""))); y = int(yy.group(1)) if yy else 9999
            if y > 2002 or y < 1980: continue
            st["le2002"] += 1
            t = clean(body(m))
            if len(t) < 80 or len(t) > 20000: continue
            s, c = score(t)
            if s < 12: continue
            h = hashlib.md5(t[:2000].encode("utf-8", "replace")).hexdigest()
            if h in seen: continue
            seen.add(h); st["kept"] += 1
            fo.write(json.dumps(dict(g=grp, y=y, date=str(m.get("Date", ""))[:40], subj=hdr(m, "Subject")[:200], frm=hdr(m, "From")[:80],
                                     score=s, c=c, text=t[:6000]), ensure_ascii=False) + "\n")
    return st
