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
HALLUCINATED = {"thank you", "thank you very much", "thanks for watching", "thank you for watching",
                "you", "bye", "thank you so much", "thanks"}


def nm(w):
    return re.sub(r"[^a-z0-9']", "", w.lower())


def _near(w, shown):
    """A heard word matches what was on screen, allowing for a word clipped at the read's edge."""
    for s in shown:
        if w == s or (len(s) > 2 and (w in s or s in w)) or (len(w) > 3 and len(s) > 3 and w[:3] == s[:3]):
            return True
    return False


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
        # WHISPER INVENTS WORDS IN A PAUSE (4 Nov 2026, THE-JUDGE-DODGED-PRISON in look E): a 1.2s
        # read of the quiet after "Watch." came back "thank you very much" - its best-known
        # hallucination - and marked a correct caption wrong. Such a read says nothing.
        if " ".join(heard) in HALLUCINATED:
            continue
        on = [c for c in caps if c[0] <= t < c[1]]
        if not on:
            continue
        # the word may straddle the change, so the neighbours count too - by TIME, not by caption
        # count (4 Nov 2026): one caption either side was ~15 words for 5-word captions and ~7 for
        # look E's 2-3 word ones, so a correctly timed look E clip failed (5 of 8). What was on
        # screen from 1.0s before to 1.4s after the moment (the 1.2s read) is the same for any look.
        shown = set()
        for c in caps:
            if c[1] > t - 1.0 and c[0] < t + 1.4:
                shown |= {nm(w) for w in c[2].split()}
        # A 1.2s read cuts words at its edges (10 Nov 2026, LIBERACE held at 8 of 12 for a correct
        # caption): "1940" for "1948.", "national" for "international", a lone "a". A clipped word is
        # still the word: match by containment (3+ letters) or a shared 3-character start, over
        # the first three heard words; a read of only one- or two-letter words says nothing.
        if not [w for w in heard if len(w) > 2]:
            continue
        if any(_near(w, shown) for w in heard[:3] if len(w) > 2):
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
