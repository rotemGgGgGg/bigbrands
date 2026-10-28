"""Builds audio/mix.wav for the REBIRTH 15s spot.

Sound effects are synthesised here (no third-party samples). The voiceover (George, ElevenLabs)
and the underscore (ElevenLabs Music) are in audio/src. The music is ducked under the voice with a
sidechain compressor, then the mix is normalised to -14 LUFS / -1.5 dBTP.
"""
import subprocess
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

HERE = Path(__file__).parent
SRC = HERE / "src"
SR = 48000
DUR = 15.0
N = int(SR * DUR)

# voiceover placement (seconds) — matches the scene timing in index.html
VO = {"s1": 1.90, "s2": 5.15, "s3": 10.45}

rng = np.random.default_rng(11)
L = np.zeros(N)
R = np.zeros(N)


def add(sig, t, gain=1.0, pan=0.0):
    i = int(t * SR)
    j = min(N, i + len(sig))
    s = sig[: j - i] * gain
    L[i:j] += s * np.sqrt((1 - pan) / 2) * 1.414
    R[i:j] += s * np.sqrt((1 + pan) / 2) * 1.414


def bandpass(x, lo, hi):
    return sosfilt(butter(2, [lo, hi], "band", fs=SR, output="sos"), x)


def whoosh(dur, f0, f1):
    """Filtered-noise sweep with a soft bell-shaped envelope."""
    n = int(dur * SR)
    noise = rng.standard_normal(n)
    out = np.zeros(n)
    blk = 1024
    for i in range(0, n, blk):
        fc = f0 * (f1 / f0) ** (i / n)
        seg = bandpass(noise[max(0, i - 2048): i + blk], fc * 0.6, fc * 1.6)
        out[i: i + blk] = seg[-len(out[i: i + blk]):]
    return out * np.sin(np.pi * np.linspace(0, 1, n)) ** 2


def crown_click(pitch=3400.0):
    """Short mechanical click: a damped transient plus a faint metallic ping."""
    n = int(0.09 * SR)
    t = np.arange(n) / SR
    transient = bandpass(rng.standard_normal(n), 1800, 8000) * np.exp(-t / 0.0025)
    ping = np.sin(2 * np.pi * pitch * t) * np.exp(-t / 0.018) * 0.35
    return (transient + ping) * np.minimum(1, t / 0.0006)


def soft_hit():
    """Low, warm accent for the logo reveal."""
    n = int(1.2 * SR)
    t = np.arange(n) / SR
    body = np.sin(2 * np.pi * 55 * t) * np.exp(-t / 0.35)
    air = bandpass(rng.standard_normal(n), 3000, 9000) * np.exp(-t / 0.25) * 0.15
    return (body + air) * np.minimum(1, t / 0.01)


add(whoosh(1.3, 300, 2600), 0.15, 0.05)            # logo reveal sweep
add(soft_hit(), 0.32, 0.10)
add(whoosh(0.8, 2400, 500), 1.75, 0.035, pan=-0.3)  # logo settles top-left
add(whoosh(0.75, 500, 4200), 4.55, 0.07, pan=0.2)   # scene 1 -> 2
add(whoosh(0.8, 4200, 400), 9.55, 0.07, pan=-0.2)   # scene 2 -> 3
for t, p in [(5.32, 3400), (7.02, 3600), (8.12, 3800), (11.62, 3200), (12.95, 2800)]:
    add(crown_click(p), t, 0.07, pan=0.15)

sfx = np.clip(np.stack([L, R], 1), -1, 1)
wavfile.write(HERE / "sfx.wav", SR, (sfx * 32767).astype(np.int16))

vo_inputs, vo_filters = [], []
for k, (name, t) in enumerate(VO.items()):
    vo_inputs += ["-i", str(SRC / f"george_{name}.mp3")]
    ms = int(t * 1000)
    vo_filters.append(f"[{k}]aresample={SR},adelay={ms}|{ms}[v{k}]")
graph = ";".join(vo_filters) + ";" + "".join(f"[v{k}]" for k in range(len(VO))) + \
    f"amix=inputs={len(VO)}:normalize=0,pan=stereo|c0=c0|c1=c0,apad=whole_dur={DUR},atrim=0:{DUR}," \
    "highpass=f=70,acompressor=threshold=-20dB:ratio=2.5:attack=5:release=120:makeup=2[vo]"
subprocess.run(["ffmpeg", "-v", "error", "-y", *vo_inputs, "-filter_complex", graph, "-map", "[vo]", str(HERE / "vo.wav")], check=True)

subprocess.run([
    "ffmpeg", "-v", "error", "-y",
    "-i", str(SRC / "music.mp3"), "-i", str(HERE / "vo.wav"), "-i", str(HERE / "sfx.wav"),
    "-filter_complex",
    f"[0]aresample={SR},atrim=0:{DUR},afade=t=in:st=0:d=0.4,afade=t=out:st={DUR - 1.2}:d=1.2,volume=0.55[m];"
    "[1]asplit=2[v][vsc];"
    "[m][vsc]sidechaincompress=threshold=0.03:ratio=5:attack=25:release=420:makeup=1[md];"
    "[md][v][2]amix=inputs=3:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=9[out]",
    "-map", "[out]", "-ar", str(SR), str(HERE / "mix.wav"),
], check=True)
print("wrote", HERE / "mix.wav")
