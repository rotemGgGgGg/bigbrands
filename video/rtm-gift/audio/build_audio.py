"""Builds audio/mix.wav for the "המתנה" reel.

Voice: Viktor (see video/VOICE.md), chosen take src/viktor_c/voice.mp3 (script_v2.txt, pitch spread 9.87 st).
Three long pauses are trimmed. Music: ElevenLabs Music. Sound effects are synthesised here.
"""
import subprocess
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

HERE = Path(__file__).parent
SRC = HERE / "src"
SR = 48000
DUR = 20.0
N = int(SR * DUR)
VO_START = 0.25
KEEP = [(0.00, 3.55), (3.85, 6.95), (7.30, 14.50), (14.90, 19.65)]    # cuts sit inside silences
# word times in the video (same as W in index.html)
W = dict(ein=1.93, shaon=4.18, yomuledet=7.27, chaver=8.24, bat=9.20, o=10.65, tishim=12.16, ad=13.52, shloshim=14.48, aval=16.85, link=17.92)
LID_OPENS = 4.98     # the site animation's lid starts to lift (frame 22 of the recording, from 4.25s)

rng = np.random.default_rng(31)
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


def pop(f=900.0):
    n = int(0.11 * SR)
    t = np.arange(n) / SR
    freq = f * (1 + 0.8 * np.exp(-t / 0.012))
    body = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t / 0.03)
    click = bp(rng.standard_normal(n), 2500, 9000) * np.exp(-t / 0.002) * 0.25
    return (body + click) * np.minimum(1, t / 0.001)


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
    n = int(dur * SR)
    t = np.arange(n) / SR
    return sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / d) for r, a, d in ((1, 1, .6), (2.0, .35, .35), (3.01, .18, .2))) * np.minimum(1, t / 0.003)


def sparkle(notes=(1568, 1976, 2349, 2794, 3136), dur=1.8):
    out = np.zeros(int(dur * SR))
    for k, f in enumerate(notes):
        b = bell(f, dur)
        d = int(k * 0.07 * SR)
        out[d:] += b[: len(out) - d]
    return out


def reveal():
    n = int(1.6 * SR)
    t = np.arange(n) / SR
    sub = np.sin(2 * np.pi * (48 + 60 * np.exp(-t / 0.05)) * t) * np.exp(-t / 0.28)
    slap = bp(rng.standard_normal(n), 800, 6000) * np.exp(-t / 0.012) * 0.6
    return sub * 0.9 + bell(1318.5) * 0.25 + slap


for k, key in enumerate(["ein", "shaon", "yomuledet", "chaver", "bat", "o", "ad", "shloshim", "aval", "link"]):
    add(pop(800 + 40 * k), W[key], 0.09)
add(pop(1100), W["link"] + 0.25, 0.09)
add(whoosh(1.1, 300, 2600), LID_OPENS - 0.15, 0.05)
add(sparkle(), LID_OPENS + 0.55, 0.035, pan=-0.15)
add(reveal(), W["tishim"], 0.15)

wavfile.write(HERE / "sfx.wav", SR, (np.clip(np.stack([L, R], 1), -1, 1) * 32767).astype(np.int16))

parts = ";".join(f"[0]atrim={a}:{b},asetpts=PTS-STARTPTS,afade=t=in:d=0.015,afade=t=out:st={b - a - 0.015:.3f}:d=0.015[p{i}]" for i, (a, b) in enumerate(KEEP))
graph = (f"{parts};" + "".join(f"[p{i}]" for i in range(len(KEEP))) + f"concat=n={len(KEEP)}:v=0:a=1,aresample={SR},"
         f"adelay={int(VO_START * 1000)}|{int(VO_START * 1000)},pan=stereo|c0=c0|c1=c0,apad=whole_dur={DUR},atrim=0:{DUR},"
         "highpass=f=80,acompressor=threshold=-20dB:ratio=2.5:attack=5:release=120:makeup=2[vo]")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(SRC / "viktor_c" / "voice.mp3"), "-filter_complex", graph, "-map", "[vo]", str(HERE / "vo.wav")], check=True)

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
