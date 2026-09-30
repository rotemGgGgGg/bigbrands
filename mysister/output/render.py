import json, math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageOps, ImageFilter, ImageDraw, ImageFont, ImageEnhance

S = '/tmp/claude-0/-home-user-bigbrands/e1e1fabc-a63d-55e9-a91a-a65f1a19c28d/scratchpad'
SRC = '/home/user/bigbrands/mysister/mysister'
OUT = sys.argv[1] if len(sys.argv) > 1 else f'{S}/work/video_silent.mp4'
PREVIEW = os.environ.get('PREVIEW')  # "t1,t2,..." -> write stills only
W, H, FPS = 1920, 1080, 30
INTRO = 4.2            # seconds before her voice starts
FONT = f'{S}/fonts/Heebo.ttf'

def P(n):
    return f'{SRC}/WhatsApp Image 2026-09-30 at {n}.jpeg'

# ---------- transcript -> subtitle phrases ----------
FIX = {('לך', 'יום'): ('לכם', 'היום')}
segs = json.load(open(f'{S}/work/transcript.json'))
words = []
for s in segs:
    for w in s['words']:
        words.append([w['w'].strip(), w['s'], w['e']])
for i in range(len(words) - 1):
    k = (words[i][0], words[i + 1][0])
    if k in FIX:
        words[i][0], words[i + 1][0] = FIX[k]

phrases = []
for s in segs:
    ws = [w for w in words if s['start'] - 0.01 <= w[1] < s['end'] + 0.01 and w not in sum([p for p in phrases], [])]
    # split long segments into chunks of <= 6 words, breaking after commas when possible
    cur = []
    for w in ws:
        cur.append(w)
        if len(cur) >= 6 or (w[0].endswith(',') and len(cur) >= 3 and len(ws) > 6):
            phrases.append(cur); cur = []
    if cur:
        if len(cur) <= 2 and phrases and len(phrases[-1]) + len(cur) <= 8 and phrases[-1][-1][2] > s['start']:
            phrases[-1] += cur
        else:
            phrases.append(cur)

def clean(t):
    return t.rstrip('.,')

subs = []
for i, p in enumerate(phrases):
    start = p[0][1] - 0.15
    end = p[-1][2] + 0.35
    if i + 1 < len(phrases):
        end = min(end, phrases[i + 1][0][1] - 0.2)
    subs.append({'start': start + INTRO, 'end': end + INTRO,
                 'words': [(clean(w[0]), w[1] + INTRO) for w in p]})

# ---------- photo timeline (anchored to what she says) ----------
# (voice time where this group starts, [photos])
groups = [
    (0.0,  ['15.51.49 (2)', '15.59.45']),                       # hi, I'm Michaela / Mitzpe Ramon
    (5.3,  ['15.51.50 (4)', '15.51.49 (4)']),                   # grew up, quiet desert, kids
    (11.1, ['15.51.49 (10)', '15.53.18', '15.51.49']),          # small community, everyone on the street
    (16.4, ['15.51.50 (1)', '15.51.55 (1)', '15.51.55', '15.51.55 (3)']),  # everyday life, home
    (27.1, ['15.52.03 (1)', '15.52.03']),                       # today, no longer live there
    (34.4, ['15.51.50 (3)', '15.53.18 (1)', '15.51.49 (1)', '15.51.50 (5)']),  # community, people of all backgrounds
    (44.8, ['15.51.49 (9)', '15.51.56 (1)', '15.51.49 (8)', '15.51.49 (7)', '15.51.50 (2)', '15.51.49 (6)']),  # slow pace, space to explore
    (53.5, ['15.52.03 (2)', '15.59.52 (1)', '15.53.18 (2)', '15.53.18 (3)', '15.59.53']),  # seven years, grew and changed
    (65.0, ['15.51.49 (3)', '15.51.50 (6)', '15.59.51', '15.51.49 (5)', '15.59.44', '15.59.45 (3)']),  # first home, childhood memories
    (77.1, ['15.59.44 (1)', '15.51.56', '15.59.45 (2)', '15.59.45 (1)']),  # places that belong to us
    (84.0, ['15.59.52']),                                       # ...belong to me (sunset)
]
VOICE_END = 88.0
OUTRO = 4.5
TOTAL = INTRO + VOICE_END + OUTRO
XF = 0.9  # crossfade seconds

shots = []  # (start, end, path)
for gi, (t0, ps) in enumerate(groups):
    t1 = groups[gi + 1][0] if gi + 1 < len(groups) else VOICE_END + OUTRO
    d = (t1 - t0) / len(ps)
    for j, p in enumerate(ps):
        shots.append([INTRO + t0 + j * d, INTRO + t0 + (j + 1) * d, P(p)])
shots[0][0] = INTRO - 0.6  # first photo emerges from the title

# ---------- image prep: warm desert grade ----------
def grade(im):
    a = np.asarray(im).astype(np.float32) / 255.0
    lum = (a * [0.299, 0.587, 0.114]).sum(2, keepdims=True)
    a = lum + (a - lum) * 0.88                       # soften saturation
    a = a * [1.04, 1.0, 0.92] + [0.012, 0.006, 0.0]   # warm sand tint
    a = 0.03 + a * 0.95                                # lifted, filmic blacks
    a = np.clip(a, 0, 1) ** 0.97
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
vig = 1 - 0.2 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) ** 1.4
vig = np.clip(vig, 0.7, 1)[..., None].astype(np.float32)

cache = {}
def prepared(path):
    """Returns a 16:9 canvas at 1.25x output size (headroom for zoom)."""
    if path in cache:
        return cache[path]
    im = ImageOps.exif_transpose(Image.open(path)).convert('RGB')
    im = grade(im)
    CW, CH = int(W * 1.25), int(H * 1.25)
    r = im.width / im.height
    if r > 1.25:  # landscape: fill
        canvas = ImageOps.fit(im, (CW, CH), Image.LANCZOS)
    else:         # portrait/square: blurred backdrop + framed photo
        bg = ImageOps.fit(im, (CW // 4, CH // 4), Image.LANCZOS).filter(ImageFilter.GaussianBlur(10))
        bg = ImageEnhance.Brightness(bg.resize((CW, CH), Image.LANCZOS)).enhance(0.55)
        ph = CH * 0.88
        fg = im.resize((int(ph * r), int(ph)), Image.LANCZOS)
        sh = Image.new('L', (CW, CH), 0)
        ox, oy = (CW - fg.width) // 2, (CH - fg.height) // 2
        ImageDraw.Draw(sh).rectangle([ox + 10, oy + 18, ox + fg.width + 10, oy + fg.height + 18], fill=150)
        sh = sh.filter(ImageFilter.GaussianBlur(28))
        bg.paste(Image.new('RGB', (CW, CH), (10, 6, 2)), (0, 0), sh)
        bg.paste(fg, (ox, oy))
        canvas = bg
    cache[path] = canvas
    return canvas

def ease(t):
    t = min(max(t, 0), 1)
    return t * t * (3 - 2 * t)

def kenburns(path, t, idx):
    c = prepared(path)
    CW, CH = c.size
    z0, z1 = (1.25, 1.12) if idx % 2 == 0 else (1.12, 1.25)   # alternate zoom in / out
    z = z0 + (z1 - z0) * t
    cw, ch = CW / z * (W / CW) * (CW / W), CH / z * (H / CH) * (CH / H)
    cw, ch = W * 1.25 / z, H * 1.25 / z
    dx = [0.35, -0.35, 0.2, -0.2][idx % 4] * (CW - cw) * (t - 0.5)
    dy = [0.15, -0.1, -0.15, 0.1][idx % 4] * (CH - ch) * (t - 0.5)
    x0 = (CW - cw) / 2 + dx
    y0 = (CH - ch) / 2 + dy
    return c.transform((W, H), Image.AFFINE, (cw / W, 0, x0, 0, ch / H, y0), resample=Image.BICUBIC)

# ---------- title (photo-filled "knockout" letters) ----------
title_bg = prepared(P('15.51.49 (2)'))  # overwritten below; placeholder load
crater = grade(ImageOps.exif_transpose(Image.open(P('15.59.45'))).convert('RGB'))
crater = ImageOps.fit(crater, (W, H), Image.LANCZOS)
sunset = grade(ImageOps.exif_transpose(Image.open(P('15.59.52'))).convert('RGB'))
sunset = ImageOps.fit(sunset, (W, H), Image.LANCZOS)

def make_mask(text, size, weight=900):
    f = ImageFont.truetype(FONT, size)
    try:
        f.set_variation_by_axes([weight])
    except Exception:
        pass
    m = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(m)
    bb = d.textbbox((0, 0), text, font=f, direction='rtl')
    d.text(((W - (bb[2] - bb[0])) / 2 - bb[0], (H - (bb[3] - bb[1])) / 2 - bb[1] - 20), text, font=f, fill=255, direction='rtl')
    return m

title_mask = make_mask('מצפה רמון', 330)
sub_f = ImageFont.truetype(FONT, 40); sub_f.set_variation_by_axes([300])
sand = (228, 206, 170)

def title_frame(t, img, mask, subtitle, fade_out_at):
    """Dark sand backdrop, letters filled with the photo, slow push-in."""
    z = 1.0 + 0.05 * (t / 6)
    cw, ch = W / z, H / z
    base = img.transform((W, H), Image.AFFINE, (cw / W, 0, (W - cw) / 2, 0, ch / H, (H - ch) / 2), resample=Image.BICUBIC)
    bg = ImageEnhance.Brightness(base.filter(ImageFilter.GaussianBlur(18))).enhance(0.38)
    reveal = ease((t - 0.2) / 1.6)
    # letters rise and sharpen in
    m = mask.transform((W, H), Image.AFFINE, (1, 0, 0, 0, 1, -30 * (1 - reveal)))
    m = m.filter(ImageFilter.GaussianBlur(10 * (1 - reveal) + 0.01)).point(lambda v: int(v * reveal))
    out = bg.copy()
    out.paste(ImageEnhance.Brightness(base).enhance(1.12), (0, 0), m)
    # thin sand line + subtitle
    a = ease((t - 1.1) / 1.2)
    if a > 0:
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        lw = int(220 * a)
        d.rectangle([W / 2 - lw / 2, 745, W / 2 + lw / 2, 747], fill=sand + (int(200 * a),))
        bb = d.textbbox((0, 0), subtitle, font=sub_f, direction='rtl')
        d.text(((W - (bb[2] - bb[0])) / 2 - bb[0], 775), subtitle, font=sub_f, fill=sand + (int(235 * a),), direction='rtl')
        out = Image.alpha_composite(out.convert('RGBA'), lay).convert('RGB')
    return out

# ---------- subtitles ----------
SUB_SIZE = 64
sf = ImageFont.truetype(FONT, SUB_SIZE); sf.set_variation_by_axes([600])
SPACE = 16
glyph_cache = {}
def word_img(w):
    if w in glyph_cache:
        return glyph_cache[w]
    d = ImageDraw.Draw(Image.new('L', (1, 1)))
    bb = d.textbbox((0, 0), w, font=sf, direction='rtl')
    im = Image.new('L', (bb[2] - bb[0] + 40, SUB_SIZE * 2), 0)
    ImageDraw.Draw(im).text((20 - bb[0], 20), w, font=sf, fill=255, direction='rtl')
    glyph_cache[w] = im
    return im

SUB_Y = H - 170
TXT = (250, 245, 236)
def draw_subs(frame, t):
    for s in subs:
        if not (s['start'] - 0.05 <= t <= s['end'] + 0.45):
            continue
        out_a = 1 - ease((t - s['end']) / 0.4)
        imgs = [word_img(w) for w, _ in s['words']]
        total = sum(i.width - 40 for i in imgs) + SPACE * (len(imgs) - 1)
        x = W / 2 + total / 2  # RTL: start at right edge
        alpha = Image.new('L', (W, H), 0)
        for (w, ws), im in zip(s['words'], imgs):
            a = ease((t - (ws - 0.12)) / 0.38) * out_a
            x -= im.width - 40
            if a > 0.003:
                dy = 14 * (1 - a) if out_a >= 1 else -8 * (1 - out_a)
                alpha.paste(Image.eval(im, lambda v, a=a: int(v * a)), (int(x - 20), int(SUB_Y - 20 + dy)), Image.eval(im, lambda v, a=a: int(v * a)))
            x -= SPACE
        # soft shadow for legibility on bright sand/sky
        shadow = alpha.filter(ImageFilter.GaussianBlur(12)).point(lambda v: min(255, int(v * 2.0)))
        frame.paste((20, 12, 4), (0, 0), shadow.point(lambda v: int(v * 0.85)))
        frame.paste(TXT, (0, 0), alpha)
    return frame

# ---------- end card ----------
end_mask = make_mask('מצפה רמון', 210)
def end_frame(t):
    # t: seconds since voice end
    return title_frame(2.0 + t * 0.5, sunset, end_mask, 'המקום ששייך לי', 0)

grain_rng = np.random.default_rng(7)
grains = [grain_rng.normal(0, 3.2, (H // 2, W // 2, 1)).astype(np.float32) for _ in range(8)]

def photo_at(t):
    cur = [(i, s) for i, s in enumerate(shots) if s[0] - XF / 2 <= t < s[1] + XF / 2]
    out = None
    for i, (a, b, p) in cur:
        prog = (t - (a - XF / 2)) / (b - a + XF)
        im = kenburns(p, prog, i)
        if out is None:
            out = im
        else:
            k = ease((t - (b if False else a) + XF / 2) / XF)
            out = Image.blend(out, im, k)
    return out

def frame_at(t):
    if t < INTRO:
        f = title_frame(t, crater, title_mask, 'הבית הראשון שלי', INTRO)
        k = ease((t - (INTRO - 0.9)) / 0.9)
        if k > 0:
            f = Image.blend(f, photo_at(max(t, shots[0][0])), k)
    else:
        f = photo_at(t)
        tv = t - INTRO
        if tv > VOICE_END + 0.3:
            k = ease((tv - VOICE_END - 0.3) / 1.2)
            f = Image.blend(f, end_frame(tv - VOICE_END - 0.3), k)
    f = draw_subs(f, t)
    a = np.asarray(f).astype(np.float32) * vig
    g = grains[int(t * FPS) % 8]
    a += np.repeat(np.repeat(g, 2, 0), 2, 1)
    # fade in from / out to black
    fade = min(ease(t / 0.8), ease((TOTAL - t) / 1.2))
    a *= fade
    return np.clip(a, 0, 255).astype(np.uint8)

if PREVIEW:
    for tt in PREVIEW.split(','):
        Image.fromarray(frame_at(float(tt))).save(f'{S}/work/prev_{tt}.jpg', quality=88)
    sys.exit()

json.dump(subs, open(f'{S}/work/subs.json', 'w'), ensure_ascii=False, indent=1)
n = int(TOTAL * FPS)
ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                       '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', OUT], stdin=subprocess.PIPE)
for i in range(n):
    ff.stdin.write(frame_at(i / FPS).tobytes())
    if i % 150 == 0:
        print(f'{i}/{n}', flush=True)
ff.stdin.close(); ff.wait()
print('done', OUT, TOTAL)
