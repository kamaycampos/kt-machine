#!/usr/bin/env python3
"""Is the word Kevin is saying ON SCREEN at that moment? Sampled, from the file.

23 Sept 2026. The older check (vsc_v2_verify) compares our times against whisper's
reading of the WHOLE clip - and that reading is the very thing the re-timing
corrects, because it compresses Kevin's hesitations and pushes everything after
them early. Measured against it, a correct caption now looks wrong: it reports a
+2.10s "error" on BREATH-OF-FIRE at exactly the word ("prison") that was proved by
ear and by short reads to be right. A referee cannot be the thing under appeal.

So this asks the question Kamay actually asks when he watches. Pick a moment at
random, read 1.2s of audio from it - short reads do not drift - and check that the
first word heard is in the caption on screen at that moment. Nothing here uses the
onsets the anchoring used, so it is not marking its own work.
"""
import json, os, random, re, subprocess, sys

FF = os.path.expanduser("~/Kamay/bin/ffmpeg")
WH = os.path.expanduser("~/Kamay/whisper.cpp/build/bin/whisper-cli")
MD = os.path.expanduser("~/Kamay/whisper.cpp/models/ggml-small.en.bin")
SAMPLES = 12


def nm(w):
    return re.sub(r"[^a-z0-9']", "", w.lower())


def check(mp4, n=SAMPLES, seed=7):
    # A clip can exist WITHOUT its caption sidecar: REPLACE-THE-HABIT was rendered
    # and the run was stopped before the sidecar was written. Say so instead of
    # taking the whole check down with a missing file.
    side = mp4[:-4] + "__caps.json"
    if not os.path.exists(side):
        return None
    caps = [tuple(x) for x in json.load(open(side))]
    if not caps:
        return None
    rnd = random.Random(seed + len(caps))
    end = caps[-1][1]
    hit = miss = 0
    misses = []
    for _ in range(n):
        t = rnd.uniform(caps[0][0] + 0.5, max(caps[0][0] + 1.0, end - 1.6))
        subprocess.run([FF, "-y", "-loglevel", "error", "-ss", f"{t:.3f}", "-t", "1.2",
                        "-i", mp4, "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", "/tmp/v2os.wav"],
                       check=True)
        r = subprocess.run([WH, "-m", MD, "-f", "/tmp/v2os.wav", "-bs", "5", "-nt"],
                           capture_output=True, text=True).stdout
        heard = [nm(w) for w in re.sub(r"\[.*?\]|\(.*?\)", " ", r).split() if nm(w)]
        if not heard:
            continue
        on = [c for c in caps if c[0] <= t < c[1]]
        if not on:
            continue
        # the word may straddle the change, so the neighbours count too
        i = caps.index(on[0])
        shown = set()
        for c in caps[max(0, i - 1):i + 2]:
            shown |= {nm(w) for w in c[2].split()}
        if heard[0] in shown or (len(heard) > 1 and heard[1] in shown):
            hit += 1
        else:
            miss += 1
            misses.append((round(t, 2), heard[:3], on[0][2][:28]))
    return hit, miss, misses


if __name__ == "__main__":
    import glob
    fs = sys.argv[1:] or sorted(glob.glob(os.path.expanduser("~/Desktop/VSC/Clips_v2/*.mp4")))
    H = M = 0
    for f in fs:
        r = check(f)
        if not r:
            continue
        h, m, misses = r
        H += h; M += m
        name = re.sub(r"_\d+s$", "", os.path.basename(f)[:-4])
        print(f"  {name:30} {h:2d}/{h+m:2d} moments the word was on screen"
              + ("" if not misses else f"   miss: {misses[0][1]} vs caption {misses[0][2]!r}"), flush=True)
    print(f"ALL: {H} of {H+M} sampled moments correct ({100*H/max(1,H+M):.0f}%)")
    print("ONSCREENDONE")
