"""Builds audio/mix.wav for the "בצבע של האאוטפיט" reel.

Voice: Viktor (see video/VOICE.md), take src/viktor/voice.mp3 (take 6, pitch spread 11.08 st, every word verified).
Pauses trimmed by video/tools/trim_plan.py --max 0.55 --keep 0.35. Music: ElevenLabs Music. SFX synthesised here:
a picker click on every colour sample, and a "ding" on every "יש" that climbs one step each time.
"""
import subprocess
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

HERE = Path(__file__).parent
SRC = HERE / "src"
SR = 48000
DUR = 17.6
N = int(SR * DUR)
VO_START = 0.25
KEEP = [(0.0, 2.22), (3.142, 4.443), (4.983, 6.697), (6.909, 8.757), (9.056, 9.89), (10.112, 11.009), (11.327, 12.171),
        (12.47, 13.493), (14.147, 17.498), (18.086, 20.556)]
# word times in the video (same as W in index.html)
W = dict(naalaim=1.13, sweatshirt=1.65, aval=2.60, shaon=3.07, bordo=3.95, yes1=4.95, menta=5.69, yes2=6.82, lavan=7.55, yes3=8.54,
         navy=9.32, yes4=10.40, beseva=11.10, bli=12.99, tishim=14.44, link=15.96)

rng = np.random.default_rng(61)
L = np.zeros(N)
R = np.zeros(N)


def add(sig, t, gain=1.0, pan=0.0):
    i = int(t * SR)
    j = min(N, i + len(sig))
    s = sig[: j - i] * gain
    L[i:j] += s * np.sqrt((1 - pan) / 2) * 1.414
    R[i:j] += s * np.sqrt((1 + pan) / 2) * 1.414


def bp(x, lo, hi):
    return sosfilt(butter(2, [lo, hi], "band", fs=SR, output="sos"), x)


def pick():
    """Colour-picker click: a short tick and a tiny upward blip."""
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    tick = bp(rng.standard_normal(n), 2000, 9000) * np.exp(-t / 0.002)
    f = 1400 * (1 + 0.5 * t / t[-1])
    blip = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.035) * 0.5
    return tick + blip


def glide(dur=0.35):
    n = int(dur * SR)
    return bp(rng.standard_normal(n), 2500, 8000) * np.sin(np.pi * np.linspace(0, 1, n)) ** 2


def ding(f):
    n = int(1.2 * SR)
    t = np.arange(n) / SR
    s = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / d) for r, a, d in ((1, 1, .45), (2.0, .3, .25), (3.0, .12, .15)))
    return s * np.minimum(1, t / 0.002)


def whoosh(dur, f0, f1):
    n = int(dur * SR)
    noise = rng.standard_normal(n)
    out = np.zeros(n)
    blk = 1024
    for i in range(0, n, blk):
        fc = f0 * (f1 / f0) ** (i / n)
        seg = bp(noise[max(0, i - 2048): i + blk], fc * 0.6, fc * 1.6)
        out[i: i + blk] = seg[-len(out[i: i + blk]):]
    return out * np.sin(np.pi * np.linspace(0, 1, n)) ** 2


def impact():
    n = int(1.4 * SR)
    t = np.arange(n) / SR
    sub = np.sin(2 * np.pi * (44 + 66 * np.exp(-t / 0.045)) * t) * np.exp(-t / 0.3)
    return sub + 0.4 * bp(rng.standard_normal(n), 600, 7000) * np.exp(-t / 0.02)


# hook: samples the sneakers, then the sweatshirt, then glides to the watch with a question
add(pick(), W["naalaim"] - 0.1, 0.10, pan=-0.3)
add(glide(), W["sweatshirt"] - 0.12, 0.04, pan=-0.2)
add(pick(), W["sweatshirt"] + 0.2, 0.08, pan=-0.3)
add(glide(0.42), W["shaon"] - 0.25, 0.05, pan=0.2)
add(pick(), W["shaon"], 0.07, pan=0.3)
# each colour: cut, sample, glide to the watch, ding — the dings climb C, E, G, C
notes = [1046.5, 1318.5, 1568.0, 2093.0]
for k, (c, y) in enumerate([("bordo", "yes1"), ("menta", "yes2"), ("lavan", "yes3"), ("navy", "yes4")]):
    if k > 0:
        add(whoosh(0.35, 3500, 600), W[c] - 0.18, 0.04)
    add(pick(), W[c], 0.09, pan=-0.3)
    add(glide(0.32), W[y] - 0.3, 0.04, pan=0.1)
    add(ding(notes[k]), W[y], 0.07, pan=0.25)
add(whoosh(0.5, 400, 3500), W["beseva"] - 0.15, 0.05)
add(impact(), W["tishim"], 0.12)
add(ding(2093.0), W["tishim"] + 0.02, 0.04)
add(pick(), W["link"], 0.06)

wavfile.write(HERE / "sfx.wav", SR, (np.clip(np.stack([L, R], 1), -1, 1) * 32767).astype(np.int16))

parts = ";".join(f"[0]atrim={a}:{b},asetpts=PTS-STARTPTS,afade=t=in:d=0.015,afade=t=out:st={b - a - 0.015:.3f}:d=0.015[p{i}]" for i, (a, b) in enumerate(KEEP))
graph = (f"{parts};" + "".join(f"[p{i}]" for i in range(len(KEEP))) + f"concat=n={len(KEEP)}:v=0:a=1,aresample={SR},"
         f"adelay={int(VO_START * 1000)}|{int(VO_START * 1000)},pan=stereo|c0=c0|c1=c0,apad=whole_dur={DUR},atrim=0:{DUR},"
         "highpass=f=80,acompressor=threshold=-20dB:ratio=2.5:attack=5:release=120:makeup=2[vo]")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(SRC / "viktor" / "voice.mp3"), "-filter_complex", graph, "-map", "[vo]", str(HERE / "vo.wav")], check=True)

subprocess.run([
    "ffmpeg", "-v", "error", "-y",
    "-i", str(SRC / "music.mp3"), "-i", str(HERE / "vo.wav"), "-i", str(HERE / "sfx.wav"),
    "-filter_complex",
    f"[0]aresample={SR},atrim=0:{DUR},afade=t=out:st={DUR - 1.0}:d=1.0,volume=0.5[m];"
    "[1]asplit=2[v][vsc];"
    "[m][vsc]sidechaincompress=threshold=0.03:ratio=4:attack=20:release=350:makeup=1[md];"
    "[md][v][2]amix=inputs=3:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=9[out]",
    "-map", "[out]", "-ar", str(SR), str(HERE / "mix.wav"),
], check=True)
print("wrote", HERE / "mix.wav")
