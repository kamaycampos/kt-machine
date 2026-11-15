#!/usr/bin/env python3
"""WHAT A PIECE OF MUSIC IS, IN NUMBERS (15 Nov 2026) - so a track can be compared with the
music under the reels we are measured against without anyone having to hear it.

    python factory/music_measure.py file.mp3|mp4 [more files]

 bpm        the beat (from the low band, where the kick and the 808 are)
 beat       how strongly the sound repeats at that beat, 0-1 (a pad is near 0, a drum beat 0.4+)
 bass       share of the energy under 150 Hz (808 / sub bass)
 high       share of the energy over 5 kHz (hi-hats, air)
 swing_db   loud-to-quiet range (a beat that never stops is small)
"""
import os
import subprocess
import sys

import numpy as np

K = os.path.expanduser("~/Kamay")
FF = os.path.join(K, "bin", "ffmpeg") if os.path.exists(os.path.join(K, "bin", "ffmpeg")) else "ffmpeg"
SR = 22050


def load(path, start=0, secs=45):
    raw = subprocess.run([FF, "-loglevel", "error", "-ss", str(start), "-t", str(secs), "-i", path, "-vn", "-ac", "1",
                          "-ar", str(SR), "-f", "s16le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def measure(path, start=0, secs=45):
    x = load(path, start, secs)
    if len(x) < SR * 5:
        return None
    n, hop = 1024, 512
    w = np.hanning(n)
    fr = np.lib.stride_tricks.sliding_window_view(x, n)[::hop] * w
    S = np.abs(np.fft.rfft(fr, axis=1)) ** 2
    f = np.fft.rfftfreq(n, 1 / SR)
    tot = S.sum() + 1e-12
    bass = S[:, f < 150].sum() / tot
    high = S[:, f > 5000].sum() / tot
    low = np.sqrt(S[:, f < 200].sum(axis=1) + 1e-12)                 # the kick / 808 line
    on = np.maximum(0, np.diff(np.log(low + 1e-6)))
    on = on - on.mean()
    ac = np.correlate(on, on, "full")[len(on) - 1:]
    fps = SR / hop
    lo, hi = int(fps * 60 / 180), int(fps * 60 / 60)
    lag = lo + int(np.argmax(ac[lo:hi]))
    bpm = 60 * fps / lag
    beat = float(ac[lag] / (ac[0] + 1e-9))
    env = np.sqrt(S.sum(axis=1))
    swing = 20 * np.log10((np.percentile(env, 95) + 1e-6) / (np.percentile(env, 20) + 1e-6))
    return {"bpm": round(bpm), "beat": round(beat, 2), "bass": round(float(bass), 3), "high": round(float(high), 3),
            "swing_db": round(float(swing), 1)}


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(os.path.basename(p)[:52].ljust(54), measure(p))
