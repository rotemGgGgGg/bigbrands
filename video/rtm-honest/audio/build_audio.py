"""Builds audio/mix.wav for the "בואו נהיה כנים" reel.

Voice: Viktor (see video/VOICE.md), take src/viktor_b/voice.mp3 (script_v2.txt, take 4, pitch spread 9.83 st,
every word verified). Four pauses are trimmed; the laugh and the beat before "אבל תסתכלו עליו" are kept.
Music: ElevenLabs Music, pulled back during the honest part and slammed back on "אבל". SFX synthesised here.
"""
import subprocess
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

HERE = Path(__file__).parent
SRC = HERE / "src"
SR = 48000
DUR = 23.0
N = int(SR * DUR)
VO_START = 0.25
KEEP = [(0.00, 0.65), (1.00, 2.55), (2.85, 5.60), (5.90, 15.65), (15.95, 22.80)]    # cuts sit inside silences
# word times in the video (same as W in index.html)
W = dict(rega=0.41, aval=2.63, az=5.37, ze=7.22, aval2=9.61, adom=11.53, menta=12.30, lavan=13.14, navy=14.18,
         shaon=15.22, bimchir=17.20, tishim=19.40, link=20.80)

rng = np.random.default_rng(51)
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


def riser(dur):
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
    return whoosh(dur, 300, 6000) * t ** 2


def impact():
    n = int(1.4 * SR)
    t = np.arange(n) / SR
    sub = np.sin(2 * np.pi * (42 + 70 * np.exp(-t / 0.045)) * t) * np.exp(-t / 0.32)
    crack = bp(rng.standard_normal(n), 600, 7000) * np.exp(-t / 0.02)
    return sub + 0.45 * crack


def shutter():
    """Camera-like double click for the colour cuts."""
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    c = bp(rng.standard_normal(n), 1500, 9000)
    return c * (np.exp(-t / 0.004) + 0.6 * np.exp(-np.maximum(t - 0.045, 0) / 0.004) * (t > 0.045))


def tick(f=2600.0):
    n = int(0.07 * SR)
    t = np.arange(n) / SR
    return bp(rng.standard_normal(n), 1800, 8000) * np.exp(-t / 0.003) + 0.4 * np.sin(2 * np.pi * f * t) * np.exp(-t / 0.01)


def bell(f, dur=1.6):
    n = int(dur * SR)
    t = np.arange(n) / SR
    return sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / d) for r, a, d in ((1, 1, .6), (2.0, .35, .35), (3.01, .18, .2))) * np.minimum(1, t / 0.003)


for t in [W["aval"], W["az"], W["ze"], W["shaon"], W["bimchir"]]:
    add(tick(), t, 0.06)
add(whoosh(0.7, 3000, 300), W["az"] - 0.45, 0.06, pan=-0.2)     # into the honest part
add(riser(0.65), W["aval2"] - 0.65, 0.05)                       # after the laugh, into the turn
add(impact(), W["aval2"], 0.17)
for k in ["adom", "menta", "lavan", "navy"]:
    add(shutter(), W[k] - 0.01, 0.09, pan=0.15)
add(whoosh(0.5, 400, 3500), W["shaon"] - 0.12, 0.05)
add(impact(), W["tishim"], 0.11)
add(bell(1318.5), W["tishim"] + 0.02, 0.05)
add(tick(3000), W["link"], 0.06)

wavfile.write(HERE / "sfx.wav", SR, (np.clip(np.stack([L, R], 1), -1, 1) * 32767).astype(np.int16))

parts = ";".join(f"[0]atrim={a}:{b},asetpts=PTS-STARTPTS,afade=t=in:d=0.015,afade=t=out:st={b - a - 0.015:.3f}:d=0.015[p{i}]" for i, (a, b) in enumerate(KEEP))
graph = (f"{parts};" + "".join(f"[p{i}]" for i in range(len(KEEP))) + f"concat=n={len(KEEP)}:v=0:a=1,aresample={SR},"
         f"adelay={int(VO_START * 1000)}|{int(VO_START * 1000)},pan=stereo|c0=c0|c1=c0,apad=whole_dur={DUR},atrim=0:{DUR},"
         "highpass=f=80,acompressor=threshold=-20dB:ratio=2.5:attack=5:release=120:makeup=2[vo]")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(SRC / "viktor_b" / "voice.mp3"), "-filter_complex", graph, "-map", "[vo]", str(HERE / "vo.wav")], check=True)

# music: full for the hook, pulled back for the honesty, back at full on "אבל"
a, b, c = W["az"] - 0.35, W["az"] + 0.15, W["aval2"] - 0.02
level = f"if(lt(t,{a}),1,if(lt(t,{b}),1-(t-{a})/{b - a}*0.7,if(lt(t,{c}),0.3,1)))"
subprocess.run([
    "ffmpeg", "-v", "error", "-y",
    "-i", str(SRC / "music.mp3"), "-i", str(HERE / "vo.wav"), "-i", str(HERE / "sfx.wav"),
    "-filter_complex",
    f"[0]aresample={SR},atrim=0:{DUR},volume='{level}':eval=frame,afade=t=out:st={DUR - 1.0}:d=1.0,volume=0.5[m];"
    "[1]asplit=2[v][vsc];"
    "[m][vsc]sidechaincompress=threshold=0.03:ratio=4:attack=20:release=350:makeup=1[md];"
    "[md][v][2]amix=inputs=3:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=9[out]",
    "-map", "[out]", "-ar", str(SR), str(HERE / "mix.wav"),
], check=True)
print("wrote", HERE / "mix.wav")
