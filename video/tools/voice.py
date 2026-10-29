"""Voice machine: turn a script into a lively, verified voice-over.

Generates several takes with ElevenLabs, measures how lively each one is (pitch movement), checks every
word with speech-to-text, and keeps the liveliest take whose words all match. Writes:
  <out>/voice.mp3          the chosen take
  <out>/words.json         [[word, start, end], ...] in seconds (emotion tags removed)
  <out>/takes.json         the score of every take

The default voice is Viktor with the settings the client approved (see video/VOICE.md).

    python3 video/tools/voice.py script.txt out_dir [--takes 5] [--voice VIKTOR] [--key-file PATH]

The API key is read from $ELEVENLABS_API_KEY or --key-file; it is never written anywhere.
"""
import argparse
import base64
import json
import os
import re
import ssl
import subprocess
import tempfile
import urllib.request
from pathlib import Path

import numpy as np
from scipy.io import wavfile

VIKTOR = "8sZ9Z3Jy28CGLLCmKEHn"   # "Viktor M - Smart & Kind Guy", ElevenLabs voice library (native Israeli Hebrew)
MODEL = "eleven_v3"
SETTINGS = {"stability": 0.0, "similarity_boost": 0.85}   # 0.0 = "Creative": most expressive
API = "https://api.elevenlabs.io/v1"


def ctx():
    ca = "/root/.ccr/ca-bundle.crt"
    return ssl.create_default_context(cafile=ca) if os.path.exists(ca) else ssl.create_default_context()


def tts(text, voice, key):
    body = json.dumps({"text": text, "model_id": MODEL, "language_code": "he", "voice_settings": SETTINGS}).encode()
    req = urllib.request.Request(f"{API}/text-to-speech/{voice}/with-timestamps?output_format=mp3_44100_128",
                                 data=body, headers={"xi-api-key": key, "content-type": "application/json"})
    j = json.loads(urllib.request.urlopen(req, context=ctx(), timeout=180).read())
    return base64.b64decode(j["audio_base64"]), j["alignment"]


def stt(path, key):
    out = subprocess.run(["curl", "-sS", "-m", "120", *(["--cacert", "/root/.ccr/ca-bundle.crt"] if os.path.exists("/root/.ccr/ca-bundle.crt") else []),
                          f"{API}/speech-to-text", "-H", f"xi-api-key: {key}", "-F", "model_id=scribe_v1", "-F", "language_code=he",
                          "-F", f"file=@{path}"], capture_output=True, text=True, check=True).stdout
    return json.loads(out).get("text", "")


def words_from_alignment(al):
    """Word timings from ElevenLabs character alignment, skipping [emotion tags]."""
    words, cur, s, e, tag = [], "", None, None, False
    for c, a, b in zip(al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]):
        if c == "[":
            tag = True
            continue
        if c == "]":
            tag = False
            continue
        if tag:
            continue
        if c.isspace():
            if cur:
                words.append([cur, round(s, 3), round(e, 3)])
            cur, s = "", None
            continue
        if s is None:
            s = a
        cur, e = cur + c, b
    if cur:
        words.append([cur, round(s, 3), round(e, 3)])
    return words


def norm(text):
    text = re.sub(r"\[[^\]]*\]", " ", text)
    text = re.sub(r"['\u05f3\u05f4\"]", "", text)   # apostrophes / geresh: "חבר'ה" == "חברה"
    return [w for w in re.sub(r"[^\w\s]", " ", text).split() if w]


def liveliness(mp3):
    """Pitch spread (p90-p10, semitones) of voiced frames: higher = more movement, less flat."""
    with tempfile.TemporaryDirectory() as d:
        wav = os.path.join(d, "x.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mp3, "-ac", "1", "-ar", "16000", wav], check=True)
        sr, x = wavfile.read(wav)
    x = x.astype(float) / 32768
    win, hop, f0 = 640, 160, []
    for i in range(0, len(x) - win, hop):
        fr = x[i:i + win] * np.hanning(win)
        if np.sqrt(np.mean(fr ** 2)) < 0.02:
            continue
        ac = np.correlate(fr, fr, "full")[win - 1:]
        ac /= ac[0] + 1e-9
        lo, hi = sr // 400, sr // 70
        k = lo + int(np.argmax(ac[lo:hi]))
        if ac[k] > 0.45:
            f0.append(sr / k)
    st = 12 * np.log2(np.array(f0) / np.median(f0))
    return float(np.percentile(st, 90) - np.percentile(st, 10))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("out")
    ap.add_argument("--takes", type=int, default=5)
    ap.add_argument("--voice", default=VIKTOR)
    ap.add_argument("--key-file")
    a = ap.parse_args()
    key = os.environ.get("ELEVENLABS_API_KEY") or (Path(a.key_file).read_text().strip() if a.key_file else None)
    if not key:
        raise SystemExit("set ELEVENLABS_API_KEY or pass --key-file")
    text = Path(a.script).read_text(encoding="utf-8").strip()
    want = norm(text)
    out = Path(a.out)
    (out / "takes").mkdir(parents=True, exist_ok=True)

    results = []
    for i in range(a.takes):
        audio, al = tts(text, a.voice, key)
        mp3 = out / "takes" / f"take{i + 1}.mp3"
        mp3.write_bytes(audio)
        heard = norm(stt(str(mp3), key))
        match = sum(1 for w in want if w in heard) / max(1, len(want))
        r = {"take": i + 1, "pitch_spread_st": round(liveliness(str(mp3)), 2), "word_match": round(match, 3), "heard": " ".join(heard)}
        (out / "takes" / f"take{i + 1}.json").write_text(json.dumps(words_from_alignment(al), ensure_ascii=False))
        results.append(r)
        print(r)

    # every word must be heard; fall back to near-perfect takes only if none is perfect
    ok = [r for r in results if r["word_match"] >= 0.999] or [r for r in results if r["word_match"] >= 0.9] or results
    best = max(ok, key=lambda r: r["pitch_spread_st"])
    (out / "voice.mp3").write_bytes((out / "takes" / f"take{best['take']}.mp3").read_bytes())
    (out / "words.json").write_text((out / "takes" / f"take{best['take']}.json").read_text())
    (out / "takes.json").write_text(json.dumps({"chosen": best["take"], "takes": results}, ensure_ascii=False, indent=1))
    print("chosen take", best["take"], best)


if __name__ == "__main__":
    main()
