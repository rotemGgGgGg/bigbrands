"""Builds audio/mix.wav for the POV ad "תראו מה מצאתי".

Voice: "Yael HE ad" (ElevenLabs, breathy Hebrew ad voice), src/yael/takes/take2.mp3: every word verified by speech-to-text,
the liveliest of six takes (9.2 st). Pauses trimmed by video/tools/trim_plan.py --max 0.34 --keep 0.22, played 1.06x.
Music: ElevenLabs Music (src/music.mp3), late-night R&B at 92 BPM. SFX synthesised here: phone taps, scroll swishes,
a sheet sliding up, a shimmer on the price, a scan for the try-on and a soft chime on the end card.
"""
import json
import re
import subprocess
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

HERE = Path(__file__).parent
SRC = HERE / "src"
SR = 48000
TEMPO, VO = 1.06, 0.10
KEEP = [(0.0, 0.653), (1.011, 2.174), (2.878, 4.178), (4.394, 5.906), (6.584, 7.794), (7.916, 9.676), (10.022, 16.49), (17.196, 19.546),
        (19.741, 21.883), (22.461, 23.534)]
# word clock: read from the page so picture and sound share one source
page = (HERE.parent / "index.html").read_text(encoding="utf-8")
RAW = {k: float(v) for k, v in re.findall(r"(\w+): ([0-9.]+)", page[page.index("const RAW = {"): page.index("};", page.index("const RAW = {"))])}
W = {k: (v - VO) / TEMPO + VO for k, v in RAW.items()}
DUR = round(W["end"] + 1.6, 2)
N = int(SR * DUR)

rng = np.random.default_rng(77)
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


def tap():
    """Glass tap: tiny click + soft low knock."""
    n = int(0.08 * SR)
    t = np.arange(n) / SR
    return bp(rng.standard_normal(n), 3000, 11000) * np.exp(-t / 0.001) * 0.6 + np.sin(2 * np.pi * 220 * t) * np.exp(-t / 0.012) * 0.5


def swish(dur, f0, f1):
    n = int(dur * SR)
    noise = rng.standard_normal(n)
    out = np.zeros(n)
    for i in range(0, n, 1024):
        fc = f0 * (f1 / f0) ** (i / n)
        seg = bp(noise[max(0, i - 2048): i + 1024], fc * 0.6, fc * 1.6)
        out[i: i + 1024] = seg[-len(out[i: i + 1024]):]
    return out * np.sin(np.pi * np.linspace(0, 1, n)) ** 2


def shimmer(dur=1.4):
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * f * t + k) * np.exp(-t / (0.5 - 0.08 * k)) for k, f in enumerate((1568.0, 2093.0, 2637.0, 3136.0)))
    return s * np.minimum(1, t / 0.01) * 0.3


def chime(f, dur=1.6):
    n = int(dur * SR)
    t = np.arange(n) / SR
    return sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / d) for r, a, d in ((1, 1, .6), (2.01, .35, .3), (3.0, .12, .15))) * np.minimum(1, t / 0.002)


def thump():
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * (50 + 60 * np.exp(-t / 0.04)) * t) * np.exp(-t / 0.15)


# A hook: thumb wiggle
add(swish(0.25, 1800, 900), W["tiru"], 0.025)
# B flick down the grid and back up, tap on the card
S0 = W["atar"] - 0.15
add(tap(), S0, 0.05)
add(swish(1.2, 5000, 700), S0 + 0.1, 0.05, pan=-0.2)
add(swish(0.8, 800, 3000), S0 + 1.5, 0.03, pan=0.2)
add(tap(), W["kol"] - 0.25, 0.08)
# C product sheet opens, scroll to the price, shimmer + ring on 99
add(swish(0.35, 900, 4000), W["kol"] - 0.1, 0.035)
add(swish(0.3, 3000, 900), W["tishim"] - 0.32, 0.035)
add(thump(), W["tishim"] - 0.02, 0.07)
add(shimmer(), W["tishim"], 0.06)
add(swish(0.45, 2500, 6000), W["shekel"] - 0.25, 0.02, pan=0.3)
# D magnifier: a soft slide while the finger drags
add(swish(W["veafilu"] - W["veefshar"], 1200, 2600), W["veefshar"], 0.012, pan=-0.2)
# E try-on sheet slides up, tap on upload, scan line
add(swish(0.42, 700, 3500), W["veafilu"] - 0.15, 0.04)
add(tap(), W["tmuna"] - 0.1, 0.08)
scan = swish(0.75, 2000, 7000)
add(scan, W["velirot"] - 0.15, 0.03, pan=0.3)
add(chime(1318.5), W["velirot"] + 0.45, 0.035)
# F launch price line underlined, thump on 150
add(swish(0.5, 800, 3000), W["rak"] - 0.05, 0.02)
add(thump(), W["mea"], 0.08)
# G end card
add(swish(0.35, 3500, 800), W["halink"] - 0.2, 0.035)
for f, g in ((1046.5, 0.04), (1318.5, 0.03), (1568.0, 0.025)):
    add(chime(f, 2.2), W["halink"] - 0.1, g, pan=0.1)
add(tap(), W["lemata"] - 0.1, 0.06)

wavfile.write(HERE / "sfx.wav", SR, (np.clip(np.stack([L, R], 1), -1, 1) * 32767).astype(np.int16))

parts = ";".join(f"[0]atrim={a}:{b},asetpts=PTS-STARTPTS,afade=t=in:d=0.012,afade=t=out:st={b - a - 0.012:.3f}:d=0.012[p{i}]" for i, (a, b) in enumerate(KEEP))
graph = (f"{parts};" + "".join(f"[p{i}]" for i in range(len(KEEP))) + f"concat=n={len(KEEP)}:v=0:a=1,atempo={TEMPO},aresample={SR},"
         f"adelay={int(VO * 1000)}|{int(VO * 1000)},pan=stereo|c0=c0|c1=c0,apad=whole_dur={DUR},atrim=0:{DUR},"
         "highpass=f=90,equalizer=f=3500:t=q:w=1.2:g=2.5,equalizer=f=10000:t=h:w=0.7:g=2,"
         "acompressor=threshold=-22dB:ratio=3:attack=4:release=110:makeup=2.5[vo]")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(SRC / "yael" / "takes" / "take2.mp3"), "-filter_complex", graph, "-map", "[vo]", str(HERE / "vo.wav")], check=True)

# loudnorm is single-pass here and lands a little low, so it aims slightly above -14 LUFS
subprocess.run([
    "ffmpeg", "-v", "error", "-y",
    "-i", str(SRC / "music.mp3"), "-i", str(HERE / "vo.wav"), "-i", str(HERE / "sfx.wav"),
    "-filter_complex",
    f"[0]aresample={SR},atrim=0:{DUR},afade=t=out:st={DUR - 1.0}:d=1.0,volume=0.5[m];"
    "[1]asplit=2[v][vsc];"
    "[m][vsc]sidechaincompress=threshold=0.03:ratio=5:attack=15:release=300:makeup=1[md];"
    "[md][v][2]amix=inputs=3:normalize=0,loudnorm=I=-13.5:TP=-1.5:LRA=9[out]",
    "-map", "[out]", "-ar", str(SR), str(HERE / "mix.wav"),
], check=True)
print("wrote", HERE / "mix.wav", "duration", DUR)
