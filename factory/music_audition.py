#!/usr/bin/env python3
"""MUSIC AUDITIONS IN SECONDS (15 Nov 2026). Kamay judges music by ear and I cannot hear, so
instead of one cloud build per guess (25 minutes each), the film is built ONCE with his voice
alone and every candidate track is laid under it here, at the level he approved (-27 dB, the
bed measured and set the same way episode_sound does), the picture untouched.

    python factory/music_audition.py film_without_music.mp4 out_folder "NAME" track1.mp3 track2.mp3 ...
"""
import os
import re
import subprocess
import sys

K = os.path.expanduser("~/Kamay")
FF = os.path.join(K, "bin", "ffmpeg") if os.path.exists(os.path.join(K, "bin", "ffmpeg")) else "ffmpeg"
HERE = os.path.dirname(os.path.abspath(__file__))
BED_DB = -27.0


def mean_db(path, start=8, secs=60):
    r = subprocess.run([FF, "-hide_banner", "-ss", str(start), "-t", str(secs), "-i", path, "-vn", "-af", "volumedetect",
                        "-f", "null", "-"], capture_output=True, text=True)
    m = re.search(r"mean_volume: (-?[\d.]+) dB", r.stderr)
    return float(m[1]) if m else -20.0


def lay(film, track, out, bed_db=BED_DB, skip=6.0):
    gain = bed_db - mean_db(track)
    r = subprocess.run([FF, "-y", "-loglevel", "error", "-i", film, "-stream_loop", "-1", "-ss", str(skip), "-i", track,
                        "-filter_complex",
                        f"[1:a]aresample=48000,volume={gain:.1f}dB,afade=t=in:st=0:d=1.2[m];"
                        f"[0:a]aresample=48000[v];[v][m]amix=inputs=2:normalize=0:duration=first,"
                        f"alimiter=limit=0.6:attack=4:release=60:level=disabled[a]",
                        "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out],
                       capture_output=True, text=True)
    return r.returncode == 0, gain


if __name__ == "__main__":
    film, folder, name = sys.argv[1:4]
    os.makedirs(folder, exist_ok=True)
    for k, t in enumerate(sys.argv[4:], 1):
        path = t if os.path.exists(t) else os.path.join(HERE, "music", t)
        label = os.path.basename(path)[:-4].replace("_", " ")
        out = os.path.join(folder, f"{name} - {chr(64 + k)} - {label}.mp4")
        ok, g = lay(film, path, out)
        print(("made " if ok else "FAILED ") + os.path.basename(out), f"(track moved {g:+.1f} dB to sit at {BED_DB:.0f})")
