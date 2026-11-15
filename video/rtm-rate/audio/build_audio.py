"""Builds audio/mix.wav for the RTM rating ad ("בואו נדרג את השעון הזה").

Voice: "Yael HE ad" (ElevenLabs, generated breathy Hebrew ad voice), src/yael/takes/take1.mp3: every word verified by
speech-to-text, pitch spread 12.25 st, the breathiest of the three voices tried (yael, tamar, danit). Script: src/script.txt.
Pauses trimmed by video/tools/trim_plan.py --max 0.32 --keep 0.2 --protect עשר (the beat before each "עשר" stays whole).
Music: ElevenLabs Music (src/music.mp3), dark R&B trap at 96 BPM. SFX synthesised here and mixed under the music.
"""
import subprocess
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

HERE = Path(__file__).parent
SRC = HERE / "src"
SR = 48000
DUR = 16.0
N = int(SR * DUR)
VO_START = 0.10
KEEP = [(0.0, 2.542), (3.468, 5.351), (5.861, 7.8), (8.45, 9.456), (9.78, 10.872), (11.567, 12.546), (12.747, 16.48), (16.643, 18.101)]
# word times in the video (same as W in index.html)
W = dict(az=0.46, itzuv=2.87, eser1=3.97, al=4.66, eser2=5.86, kama=6.65, achad=7.57, eser3=8.01, mechir=8.76, tishim=9.83, shekel=10.75,
         eser4=12.31, link=13.31)

rng = np.random.default_rng(1010)
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


def tick(f=2400, d=0.012):
    n = int(0.06 * SR)
    t = np.arange(n) / SR
    return bp(rng.standard_normal(n), 2500, 10000) * np.exp(-t / 0.0015) + 0.35 * np.sin(2 * np.pi * f * t) * np.exp(-t / d)


def shutter():
    """Camera shutter for each colour cut: two quick clicks."""
    return np.concatenate([tick(1800, 0.006), np.zeros(int(0.025 * SR)), 0.7 * tick(1500, 0.006)])


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


def bell(f, dur=1.6):
    """Gold 'ding' for every score: bright, slightly inharmonic, long tail."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / d) for r, a, d in ((1, 1, .7), (2.01, .4, .35), (2.76, .22, .22), (4.07, .1, .12)))
    return s * np.minimum(1, t / 0.0015)


def impact(depth=1.0):
    n = int(1.6 * SR)
    t = np.arange(n) / SR
    sub = np.sin(2 * np.pi * (40 + 70 * np.exp(-t / 0.05)) * t) * np.exp(-t / (0.25 + 0.15 * depth))
    return sub + 0.35 * bp(rng.standard_normal(n), 500, 7000) * np.exp(-t / 0.018)


def riser(dur):
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
    return whoosh(dur, 500, 6000) * t ** 1.5


def slam(t, note):
    add(impact(0.6), t, 0.10)
    add(bell(note), t + 0.005, 0.05, pan=0.15)
    add(bell(note * 1.5), t + 0.005, 0.025, pan=-0.15)
    for k in range(5):                                     # the counter rolling up to it
        add(tick(2600 + 120 * k), t - 0.24 + k * 0.048, 0.018, pan=0.35)


# hook: soft riser into the first question
add(bell(1046.5, 2.2), 0.05, 0.03)
add(riser(0.9), W["itzuv"] - 0.9, 0.035)
# 1 design: whip into the dial, gold slam on "עשר"
add(whoosh(0.4, 4000, 500), W["itzuv"] - 0.22, 0.06, pan=-0.3)
slam(W["eser1"], 1046.5)
# 2 wrist: whip out + flash in
add(whoosh(0.3, 900, 5000), W["al"] - 0.27, 0.06, pan=0.4)
add(impact(0.2), W["al"] - 0.02, 0.05)
slam(W["eser2"], 1174.7)
# 3 colours: a shutter on every cut (same curve as the picture), the last one lands on "עשר"
r0, r1 = W["kama"] + 0.05, W["eser3"]
for i in range(11):
    add(shutter(), r0 + (r1 - r0) * (i / 10) ** 0.8, 0.05 + 0.004 * i, pan=(-0.3, 0.3)[i % 2])
add(impact(0.6), r1, 0.10)
add(bell(1318.5), r1 + 0.005, 0.05)
# 4 price: riser, big hit with the ring, then the score
add(whoosh(0.3, 4000, 700), W["mechir"] - 0.2, 0.05)
add(riser(W["tishim"] - W["mechir"]), W["mechir"], 0.04)
add(impact(1.0), W["tishim"], 0.16)
add(bell(783.99, 2.0), W["tishim"] + 0.01, 0.04)
slam(W["shekel"], 1396.9)
# 5 final: stamp, chord, then a click on the link
add(whoosh(0.35, 700, 4500), W["eser4"] - 0.3, 0.05)
add(impact(1.0), W["eser4"] - 0.02, 0.14)
for f, g in ((1046.5, 0.05), (1318.5, 0.04), (1568.0, 0.035), (2093.0, 0.02)):
    add(bell(f, 2.4), W["eser4"], g, pan=0.1)
add(whoosh(0.4, 3500, 600), W["link"] - 0.3, 0.035)
add(tick(), W["link"] - 0.05, 0.06)

wavfile.write(HERE / "sfx.wav", SR, (np.clip(np.stack([L, R], 1), -1, 1) * 32767).astype(np.int16))

parts = ";".join(f"[0]atrim={a}:{b},asetpts=PTS-STARTPTS,afade=t=in:d=0.012,afade=t=out:st={b - a - 0.012:.3f}:d=0.012[p{i}]" for i, (a, b) in enumerate(KEEP))
graph = (f"{parts};" + "".join(f"[p{i}]" for i in range(len(KEEP))) + f"concat=n={len(KEEP)}:v=0:a=1,aresample={SR},"
         f"adelay={int(VO_START * 1000)}|{int(VO_START * 1000)},pan=stereo|c0=c0|c1=c0,apad=whole_dur={DUR},atrim=0:{DUR},"
         "highpass=f=90,equalizer=f=3500:t=q:w=1.2:g=2.5,equalizer=f=10000:t=h:w=0.7:g=2,"
         "acompressor=threshold=-22dB:ratio=3:attack=4:release=110:makeup=2.5[vo]")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(SRC / "yael" / "takes" / "take1.mp3"), "-filter_complex", graph, "-map", "[vo]", str(HERE / "vo.wav")], check=True)

# loudnorm runs single-pass and lands about 1.2 LU low, so it aims at -13.7 to measure -14 LUFS
subprocess.run([
    "ffmpeg", "-v", "error", "-y",
    "-i", str(SRC / "music.mp3"), "-i", str(HERE / "vo.wav"), "-i", str(HERE / "sfx.wav"),
    "-filter_complex",
    f"[0]aresample={SR},atrim=0:{DUR},afade=t=out:st={DUR - 1.0}:d=1.0,volume=0.5[m];"
    "[1]asplit=2[v][vsc];"
    "[m][vsc]sidechaincompress=threshold=0.03:ratio=5:attack=15:release=300:makeup=1[md];"
    "[md][v][2]amix=inputs=3:normalize=0,loudnorm=I=-13.7:TP=-1.5:LRA=9[out]",
    "-map", "[out]", "-ar", str(SR), str(HERE / "mix.wav"),
], check=True)
print("wrote", HERE / "mix.wav")
