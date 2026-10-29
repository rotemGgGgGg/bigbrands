"""Plan pause trims for a voice take and map its word times onto the video clock.

Long silences are shortened to --keep seconds (cut from their middle); silences before the words given in
--protect stay whole (a laugh, a dramatic beat). Prints KEEP segments (for build_audio.py) and every word's
time in the video, given the voice-over starts at --start.

    python3 video/tools/trim_plan.py voice.mp3 words.json [--max 0.6] [--keep 0.4] [--start 0.25] [--protect אבל,זה]
"""
import argparse
import json
import re
import subprocess


def silences(mp3, db=-38, min_dur=0.2):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-i", mp3, "-af", f"silencedetect=n={db}dB:d={min_dur}", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", err)]
    return list(zip(starts, ends))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mp3")
    ap.add_argument("words")
    ap.add_argument("--max", type=float, default=0.6)
    ap.add_argument("--keep", type=float, default=0.4)
    ap.add_argument("--start", type=float, default=0.25)
    ap.add_argument("--protect", default="")
    a = ap.parse_args()
    words = json.load(open(a.words))
    protect = {p.strip() for p in a.protect.split(",") if p.strip()}
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", a.mp3],
                               capture_output=True, text=True).stdout)

    cuts = []
    for s, e in silences(a.mp3):
        if e - s <= a.max:
            continue
        nxt = next((w for w in words if w[1] >= e - 0.15), None)
        if nxt and re.sub(r"[^\w]", "", nxt[0]) in protect:
            continue
        mid, half = (s + e) / 2, (e - s - a.keep) / 2
        cuts.append((round(mid - half, 3), round(mid + half, 3)))

    keep, t = [], 0.0
    for c0, c1 in cuts:
        keep.append((round(t, 3), c0))
        t = c1
    keep.append((round(t, 3), round(dur + 0.05, 3)))

    def video_time(x):
        removed = sum(c1 - c0 for c0, c1 in cuts if c1 <= x)
        return round(x - removed + a.start, 2)

    print("KEEP =", keep)
    print("removed %.2fs; voice ends at %.2fs in the video" % (sum(c1 - c0 for c0, c1 in cuts), video_time(dur)))
    for w in words:
        print(f"{video_time(w[1]):6.2f}  {w[0]}")


if __name__ == "__main__":
    main()
