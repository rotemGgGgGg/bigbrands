"""Builds audio/mix.wav for the "מה קונים ב-99 שקל" ad.

Voice: Viktor (see video/VOICE.md), src/viktor_b/takes/take7.mp3 (pitch spread 11.1 st, every word verified), script src/script_v2.txt.
Pauses trimmed by video/tools/trim_plan.py --max 0.3 --keep 0.16, then played 1.1x faster so the ad stays under 17 s.
Music: ElevenLabs Music (src/music.mp3). SFX synthesised here: bites, a meter tick, a stamp thud on each "נגמר",
a car pass, a bright chime on the watch, a tick per fact and an impact on the price.
loudnorm runs single-pass and lands about 1.2 LU low, so it aims at -12.8 to measure -14 LUFS.
"""
import subprocess
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

HERE = Path(__file__).parent
SRC = HERE / "src"
SR = 48000
DUR = 16.6
N = int(SR * DUR)
VO_START = 0.12
TEMPO = 1.1
KEEP = [(0.0, 2.491), (2.758, 5.706), (6.114, 8.536), (8.973, 11.773), (12.165, 14.335), (14.573, 16.155), (16.614, 18.084), (18.338, 19.459)]
# word times in the video (same as W in index.html)
W = dict(ma=0.52, burger=2.48, nigmar=3.87, monit=5.21, nigmera=6.13, o=7.30, shaon=7.77, nishar=8.49, kolyom=9.26, dgamim=9.87, bayit=11.05,
         hachzara=11.92, tishim=13.32, link=14.67)

rng = np.random.default_rng(99)
L = np.zeros(N)
R = np.zeros(N)


def add(sig, t, gain=1.0, pan=0.0):
    i = max(0, int(t * SR))
    j = min(N, i + len(sig))
    s = sig[: j - i] * gain
    L[i:j] += s * np.sqrt((1 - pan) / 2) * 1.414
    R[i:j] += s * np.sqrt((1 + pan) / 2) * 1.414


def bp(x, lo, hi):
    return sosfilt(butter(2, [lo, hi], "band", fs=SR, output="sos"), x)


def tick(f=1800):
    n = int(0.06 * SR)
    t = np.arange(n) / SR
    return bp(rng.standard_normal(n), 2500, 9000) * np.exp(-t / 0.0015) + 0.4 * np.sin(2 * np.pi * f * t) * np.exp(-t / 0.012)


def bite():
    """A crunchy bite: a short burst of mid noise with a low thump."""
    n = int(0.1 * SR)
    t = np.arange(n) / SR
    return bp(rng.standard_normal(n), 900, 5200) * np.exp(-t / 0.018) + 0.5 * np.sin(2 * np.pi * 150 * t) * np.exp(-t / 0.02)


def thud():
    """Rubber stamp: low thump and a slap of noise."""
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * (60 + 90 * np.exp(-t / 0.03)) * t) * np.exp(-t / 0.11) + 0.5 * bp(rng.standard_normal(n), 400, 4000) * np.exp(-t / 0.012)


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


def ding(f, dur=1.3):
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / d) for r, a, d in ((1, 1, .5), (2.0, .3, .28), (3.0, .12, .16)))
    return s * np.minimum(1, t / 0.002)


def impact():
    n = int(1.4 * SR)
    t = np.arange(n) / SR
    sub = np.sin(2 * np.pi * (44 + 66 * np.exp(-t / 0.045)) * t) * np.exp(-t / 0.3)
    return sub + 0.4 * bp(rng.standard_normal(n), 600, 7000) * np.exp(-t / 0.02)


# hook: the tag lands
add(thud(), 0.0, 0.07)
add(tick(), 0.05, 0.07)
# burger: pop in, four bites, stamp
add(whoosh(0.3, 600, 3200), W["burger"] - 0.3, 0.04)
eat = W["nigmar"] - 0.75
for k in range(4):
    add(bite(), eat + k * 0.17, 0.085, pan=(-0.25, 0.2, -0.1, 0.25)[k])
add(thud(), W["nigmar"] + 0.2, 0.13)
# taxi: slides in, drives off, stamp
add(whoosh(0.32, 600, 3200), W["monit"] - 0.28, 0.04)
for k in range(5):
    add(tick(1300), W["monit"] + 0.3 + k * 0.11, 0.03, pan=0.3)
wo = whoosh(0.45, 2600, 500)
add(wo, W["nigmera"] - 0.36, 0.07, pan=0.4)
add(wo, W["nigmera"] - 0.30, 0.05, pan=-0.5)
add(thud(), W["nigmera"] + 0.2, 0.13)
# the watch: a bright chord, then the day counter runs
add(whoosh(0.4, 500, 4000), W["shaon"] - 0.36, 0.05)
for f, g in ((1046.5, 0.07), (1318.5, 0.05), (1568.0, 0.045)):
    add(ding(f), W["shaon"] - 0.03, g, pan=0.15)
n_ticks = 16
t0, t1 = W["nishar"] + 0.3, W["dgamim"] - 0.3
for k in range(n_ticks):                                    # accelerating, like the counter
    add(tick(2200), t0 + (t1 - t0) * (1 - (1 - k / n_ticks) ** 2), 0.022 + 0.001 * k, pan=-0.3)
# facts: three rising ticks
add(whoosh(0.3, 3500, 700), W["dgamim"] - 0.2, 0.04)
for k, w in enumerate(("dgamim", "bayit", "hachzara")):
    add(ding((1318.5, 1568.0, 2093.0)[k], 0.7), W[w], 0.045, pan=(-0.2, 0, 0.2)[k])
# price + link
add(impact(), W["tishim"], 0.13)
add(ding(2093.0), W["tishim"] + 0.02, 0.04)
add(tick(), W["link"] - 0.1, 0.07)

wavfile.write(HERE / "sfx.wav", SR, (np.clip(np.stack([L, R], 1), -1, 1) * 32767).astype(np.int16))

parts = ";".join(f"[0]atrim={a}:{b},asetpts=PTS-STARTPTS,afade=t=in:d=0.012,afade=t=out:st={b - a - 0.012:.3f}:d=0.012[p{i}]" for i, (a, b) in enumerate(KEEP))
graph = (f"{parts};" + "".join(f"[p{i}]" for i in range(len(KEEP))) + f"concat=n={len(KEEP)}:v=0:a=1,atempo={TEMPO},aresample={SR},"
         f"adelay={int(VO_START * 1000)}|{int(VO_START * 1000)},pan=stereo|c0=c0|c1=c0,apad=whole_dur={DUR},atrim=0:{DUR},"
         "highpass=f=80,acompressor=threshold=-20dB:ratio=2.5:attack=5:release=120:makeup=2[vo]")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(SRC / "viktor_b" / "takes" / "take7.mp3"), "-filter_complex", graph, "-map", "[vo]", str(HERE / "vo.wav")], check=True)

subprocess.run([
    "ffmpeg", "-v", "error", "-y",
    "-i", str(SRC / "music.mp3"), "-i", str(HERE / "vo.wav"), "-i", str(HERE / "sfx.wav"),
    "-filter_complex",
    f"[0]aresample={SR},atrim=0:{DUR},afade=t=out:st={DUR - 0.9}:d=0.9,volume=0.5[m];"
    "[1]asplit=2[v][vsc];"
    "[m][vsc]sidechaincompress=threshold=0.03:ratio=4:attack=20:release=350:makeup=1[md];"
    "[md][v][2]amix=inputs=3:normalize=0,loudnorm=I=-12.8:TP=-1.5:LRA=9[out]",
    "-map", "[out]", "-ar", str(SR), str(HERE / "mix.wav"),
], check=True)
print("wrote", HERE / "mix.wav")
