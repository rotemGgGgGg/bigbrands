"""Read AVP zone bands from an OpenMarket screenshot. price(y) = label fit at (y - 4px): axis labels sit ~4 px above
their true price (calibrated on the user's hover readings and the boxed last-price label)."""
import sys, json, numpy as np
from PIL import Image
def zones(path, label_y, top_price, step, segs, y0=95, y1=880, shift=4.0):
    im = np.array(Image.open(path).convert("RGB")).astype(int)
    a, b = np.polyfit(label_y, [top_price - step * i for i in range(len(label_y))], 1)
    price = lambda y: a * (y - shift) + b
    bg = np.array([253, 246, 227]); out = {}
    for name, (xa, xb) in segs.items():
        votes = {}
        for x in np.linspace(xa + 5, xb - 5, 25).astype(int):
            col = im[:, x]; y = y0
            while y < y1:
                c = col[y]
                pale = c.min() > 150 and abs(c - bg).sum() > 25
                if pale:
                    s = y
                    while y < y1 and col[y].min() > 150 and abs(col[y] - bg).sum() > 25: y += 1
                    if 5 <= y - s <= 30:
                        m = col[(s + y) // 2]; k = "R" if m[0] > m[1] + 12 else ("G" if m[1] > m[2] + 8 and m[1] >= m[0] else "B")
                        key = (k, round(s / 2), round(y / 2)); votes[key] = votes.get(key, 0) + 1
                y += 1
        keep = sorted([k for k, v in votes.items() if v >= 6], key=lambda k: k[1])
        merged = []
        for k, s, e in keep:
            if merged and merged[-1][0] == k and abs(merged[-1][1] - s) <= 2: continue
            merged.append((k, s, e))
        out[name] = [(k, round(price(2 * e)), round(price(2 * s))) for k, s, e in merged]
    return out
if __name__ == "__main__":
    print(json.dumps(zones(**json.load(open(sys.argv[1]))), indent=0))
