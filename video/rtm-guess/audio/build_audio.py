"""Builds audio/mix.wav for the "כמה זה עלה?" reel.

Voice: Viktor (ElevenLabs voice library, eleven_v3), take 1. Long pauses are trimmed, the suspense pause
before the price is kept. Music: ElevenLabs Music. Sound effects are synthesised here.
The music drops out for the countdown and comes back on the price.
"""
import subprocess
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

HERE = Path(__file__).parent
SRC = HERE / "src"
SR = 48000
DUR = 16.4
N = int(SR * DUR)
VO_START = 0.25
# parts of the original take to keep (seconds); cuts sit inside silences
KEEP = [(0.00, 6.40), (7.20, 9.30), (9.90, 12.20), (13.10, 14.40), (14.90, 17.48)]

rng = np.random.default_rng(21)
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
    """Sticker pop: short pitched blip with a soft click."""
    n = int(0.11 * SR)
    t = np.arange(n) / SR
    freq = f * (1 + 0.8 * np.exp(-t / 0.012))
    body = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t / 0.03)
    click = bp(rng.standard_normal(n), 2500, 9000) * np.exp(-t / 0.002) * 0.25
    return (body + click) * np.minimum(1, t / 0.001)


def tick(pitch=2900.0):
    """Clock tick for the countdown."""
    n = int(0.06 * SR)
    t = np.arange(n) / SR
    return (bp(rng.standard_normal(n), 2000, 9000) * np.exp(-t / 0.003) + 0.5 * np.sin(2 * np.pi * pitch * t) * np.exp(-t / 0.008))


def reveal():
    """Price reveal: sub hit + bright bell."""
    n = int(1.6 * SR)
    t = np.arange(n) / SR
    sub = np.sin(2 * np.pi * (48 + 60 * np.exp(-t / 0.05)) * t) * np.exp(-t / 0.28)
    f = 1318.5
    bell = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / d) for r, a, d in ((1, 1, .6), (2.0, .35, .35), (3.01, .18, .2)))
    slap = bp(rng.standard_normal(n), 800, 6000) * np.exp(-t / 0.012) * 0.6
    return sub * 0.9 + bell * 0.25 + slap


def swish(dur=0.18):
    n = int(dur * SR)
    return bp(rng.standard_normal(n), 1500, 7000) * np.sin(np.pi * np.linspace(0, 1, n)) ** 2


for t, f in [(1.77, 820), (11.39, 880), (12.57, 940), (14.05, 1000), (14.30, 1100)]:
    add(pop(f), t, 0.10)
for t, f in [(4.05, 1040), (5.53, 1160)]:
    add(pop(f), t, 0.09, pan=-0.2)
add(pop(700), 6.79, 0.11)
for k, t in enumerate([6.94, 7.06, 7.18]):
    add(pop(1200 + 120 * k), t, 0.05, pan=0.2)
for k, t in enumerate([8.75, 9.15, 9.55]):
    add(tick(2700 + 200 * k), t, 0.12)
add(pop(600), 9.32, 0.08)
add(reveal(), 9.81, 0.16)
for k, t in enumerate([12.57, 12.87, 13.17, 13.47, 13.77]):
    add(swish(), t - 0.06, 0.035, pan=(-0.3 if k % 2 else 0.3))

wavfile.write(HERE / "sfx.wav", SR, (np.clip(np.stack([L, R], 1), -1, 1) * 32767).astype(np.int16))

# voice: cut the long pauses, 15 ms fades at each join, place at VO_START
parts = ";".join(f"[0]atrim={a}:{b},asetpts=PTS-STARTPTS,afade=t=in:d=0.015,afade=t=out:st={b - a - 0.015:.3f}:d=0.015[p{i}]" for i, (a, b) in enumerate(KEEP))
graph = (f"{parts};" + "".join(f"[p{i}]" for i in range(len(KEEP))) + f"concat=n={len(KEEP)}:v=0:a=1,aresample={SR},"
         f"adelay={int(VO_START * 1000)}|{int(VO_START * 1000)},pan=stereo|c0=c0|c1=c0,apad=whole_dur={DUR},atrim=0:{DUR},"
         "highpass=f=80,acompressor=threshold=-20dB:ratio=2.5:attack=5:release=120:makeup=2[vo]")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(SRC / "viktor_take1.mp3"), "-filter_complex", graph, "-map", "[vo]", str(HERE / "vo.wav")], check=True)

# music: drops for the countdown (8.55-9.78s) and slams back on the price
drop = "if(lt(t,8.55),1,if(lt(t,8.75),1-(t-8.55)/0.2*0.85,if(lt(t,9.78),0.15,1)))"
subprocess.run([
    "ffmpeg", "-v", "error", "-y",
    "-i", str(SRC / "music.mp3"), "-i", str(HERE / "vo.wav"), "-i", str(HERE / "sfx.wav"),
    "-filter_complex",
    f"[0]aresample={SR},atrim=0:{DUR},volume='{drop}':eval=frame,afade=t=out:st={DUR - 1.0}:d=1.0,volume=0.5[m];"
    "[1]asplit=2[v][vsc];"
    "[m][vsc]sidechaincompress=threshold=0.03:ratio=4:attack=20:release=350:makeup=1[md];"
    "[md][v][2]amix=inputs=3:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=9[out]",
    "-map", "[out]", "-ar", str(SR), str(HERE / "mix.wav"),
], check=True)
print("wrote", HERE / "mix.wav")
