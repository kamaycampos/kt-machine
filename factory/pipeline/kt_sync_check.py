#!/usr/bin/env python3
"""Are the captions on screen when the words are said? Checked on the FINISHED clip.

WHY THIS EXISTS. 16 Sept 2026. Captions on seven clips drifted progressively
ahead of the speech - 1.6s early by second 4, 9.5s early by second 22 - and two
of them posted. Kamay spotted it at a glance: "the captions are completely off
close to the beginning."

Nothing caught it because nothing looked. kt_verify_render listens to the first
and last seconds; a still frame shows the right caption for that instant; an
exit code of 0 says the encode worked. Drift that GROWS is invisible at the
edges and obvious in the middle.

The cause was mine: a punctuation prompt added to the word-timing pass, which
compresses whisper's timestamps. The check below would have failed every one of
those clips on its first run.

How: the renderer writes <clip>__caps.json - exactly what it burned. This
transcribes the finished clip independently, with NO prompt, and compares each
caption's first word against when that word is actually spoken.

    python3 kt_sync_check.py POST_TODAY/KT_LIES/03_THE-DRYER-FUND_57s.mp4 [...]
    exit 1 if any clip fails
"""
import json
import os
import re
import statistics as st
import subprocess
import sys

HOME = os.path.expanduser("~/Kamay")
sys.path.insert(0, HOME)
import kt_words                                                  # noqa: E402

FF = f"{HOME}/bin/ffmpeg"
W = f"{HOME}/whisper.cpp/build/bin/whisper-cli"
M = f"{HOME}/whisper.cpp/models/ggml-small.en.bin"
MEDIAN_MAX = 0.30      # a caption's typical lead, including the deliberate 0.1s lead-in
P90_MAX = 0.70         # and the worst tenth - one long burst may start a word early
LEAD_IN = 0.10


def norm(w):
    return re.sub(r"[^a-z0-9]", "", w.lower())


def check(mp4):
    """Grade each caption against the WAVEFORM, not against another transcription.

    FIRST VERSION WAS WRONG, 16 Sept 2026, the same afternoon it was written. It
    compared burned captions against a second whisper pass over the finished
    clip, and FAILED a good clip - THE ECONOMY WAS SLUGGISH, "0.4s early". Graded
    against the real sound over 50 pauses, the burned captions were off by a
    median 0.01s; the checker's own reference was the less accurate of the two.
    Two whisper runs over identical audio disagreed by 0.39s. Whisper cannot
    referee whisper.

    So: after every real pause the next word begins exactly where the sound
    rises - that moment is ground truth. Whisper supplies WHICH word starts
    there (it is reliable about words, not about milliseconds), the waveform
    supplies WHEN, and the caption for that word is graded against it.
    """
    side = os.path.splitext(mp4)[0] + "__caps.json"
    if not os.path.exists(side):
        return None, f"no {os.path.basename(side)} - render it again to get one"
    bursts = json.load(open(side))
    tmp = f"/tmp/kt_sync.{os.getpid()}"   # per process
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", mp4, "-ar", "16000", "-ac", "1",
                    "-c:a", "pcm_s16le", tmp + ".wav"], capture_output=True)
    subprocess.run([W, "-m", M, "-f", tmp + ".wav", "-ml", "1", "-sow", "-osrt", "-of", tmp],
                   capture_output=True)
    heard = kt_words.parse_word_srt(tmp + ".srt")
    r = subprocess.run([FF, "-i", tmp + ".wav", "-af", "silencedetect=noise=-38dB:d=0.25",
                        "-f", "null", "-"], capture_output=True, text=True).stderr
    onsets = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r)]
    # ALIGN BY ORDER, NOT BY NEAREST MATCH. The second version searched forward
    # for the next caption starting with the same word, and "the", "and",
    # "you" matched the wrong occurrence - reporting 16s errors on a clip whose
    # median was 0.10s. A sequence alignment of the two word lists uses word
    # ORDER, so a repeated word maps to the right instance. It still catches
    # real drift: compressed timestamps keep the words in order, only the times
    # are wrong, and the times are what gets graded.
    import difflib
    cap_words = []                       # (normalised word, burst start if it opens one)
    for a, _b, text in bursts:
        for k, w in enumerate(text.split()):
            cap_words.append((norm(w), a if k == 0 else None))
    hn = [norm(w) for _a, _b, w in heard]
    cn = [w for w, _ in cap_words]
    sm = difflib.SequenceMatcher(a=hn, b=cn, autojunk=False)
    h2c = {}
    for tag, i1, i2, j1, _j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                h2c[i1 + k] = j1 + k
    def graded(onsets):
        out = []
        for t in onsets:
            idx = [n for n, x in enumerate(heard) if t - 0.6 <= x[0] <= t + 0.6]
            if not idx:
                continue
            hi = min(idx, key=lambda n: abs(heard[n][0] - t))
            ci = h2c.get(hi)
            if ci is None or cap_words[ci][1] is None:
                continue                 # the word at this pause does not open a caption
            out.append((cap_words[ci][1] + LEAD_IN) - t)
        return out
    err, how, med_max, p90_max = graded(onsets), "", MEDIAN_MAX, P90_MAX
    # TOO FEW PAUSES IS NOT A BAD CLIP. 6 Oct 2026: 21 clips failed "too few to
    # judge" - ep_v733zpw four times a run for six runs - while nothing said
    # their captions were wrong. A room whose quiet never falls under -38 dB has
    # no "pauses" at that floor. Quiet is RELATIVE (vsc-factory: 35 dB under the
    # speech; 20 here, where only a word onset is needed): measure the clip's own
    # level and look again, still against the waveform.
    if len(err) < 5:
        lv = subprocess.run([FF, "-i", tmp + ".wav", "-af", "volumedetect", "-f", "null", "-"],
                            capture_output=True, text=True).stderr
        m = re.search(r"mean_volume: (-?[\d.]+) dB", lv)
        floor = float(m[1]) - 20 if m else -38.0
        if floor > -38.0:
            r2 = subprocess.run([FF, "-i", tmp + ".wav", "-af", f"silencedetect=noise={floor:.1f}dB:d=0.25",
                                 "-f", "null", "-"], capture_output=True, text=True).stderr
            e2 = graded([float(x) for x in re.findall(r"silence_end: ([\d.]+)", r2)])
            if len(e2) > len(err):
                err, how = e2, f" (pauses at {floor:.0f} dB)"
    # STILL TOO FEW: a music bed under every pause. Then the clip's own words are
    # the reference - whisper against whisper, which disagrees by up to ~0.4s on
    # identical audio (16 Sept), so the bar moves by exactly that and no more.
    # The 16 Sept drift (1.6s growing to 9.5s) fails this by a mile.
    if len(err) < 5:
        e3 = [(a + LEAD_IN) - heard[hi][0] for hi, ci in h2c.items()
              for a in [cap_words[ci][1]] if a is not None]
        if len(e3) >= 8:
            err, how, med_max, p90_max = e3, " (word-referenced: no clear pauses)", 0.40, 0.90
    if len(err) < 5:
        return None, f"only {len(err)} pause-anchored captions - too few to judge"
    med = st.median(err)
    p90 = sorted(abs(d) for d in err)[max(0, int(len(err) * 0.9) - 1)]
    ok = abs(med) <= med_max and p90 <= p90_max
    # AND NOTHING SPOKEN GOES UNCAPTIONED. 16 Sept 2026: a rule meant to drop a
    # half-syllable deleted five whole seconds of captions from the YWIYC
    # flagship ("...New York City at the Carnegie Deli") and the timing check
    # still passed - there was nothing left there to be late. Coverage is its
    # own question: speech with no caption over it.
    silent = [(a, b) for a, b in re.findall(r"silence_start: ([\d.]+)[\s\S]*?silence_end: ([\d.]+)", r)]
    quiet = [(float(a), float(b)) for a, b in silent]
    def speaking(t):
        return not any(a <= t <= b for a, b in quiet)
    # SOUND IS NOT SPEECH. 3 Oct 2026, member clip 1: the gate failed a gap at
    # 38.9-40.4s that is both men LAUGHING (checked frame by frame, 37.8-40.0s),
    # with every word whisper heard already captioned (100%). Loud enough to beat
    # the silence floor, but nothing there to caption. So a gap only counts when
    # whisper heard a real word inside it - clip 2's dropped "So I..." still fails.
    # Tags like [laughter] / (laughs) / *music* and pure "ha ha" are not words.
    def said(w):
        n = norm(w)
        return bool(n) and not re.match(r"^\s*[\[\(\*]", w) and not re.fullmatch(r"(ha)+h?|(he){2,}h?", n)
    holes = []
    for k in range(len(bursts) - 1):
        a, b = bursts[k][1], bursts[k + 1][0]
        if (b - a > 1.2 and speaking((a + b) / 2)
                and any(a + 0.1 <= hs < b - 0.1 and said(w) for hs, _he, w in heard)):
            holes.append((round(a, 1), round(b, 1)))
    cw = sum(len(t.split()) for _a, _b, t in bursts)
    cover = cw / max(1, len(heard))
    if holes or cover < 0.85:
        ok = False
    return ok, (f"{len(err)} captions vs the sound{how}  median {med:+.2f}s  worst-10% {p90:.2f}s  "
                f"| words captioned {cover:.0%}" + (f"  UNCAPTIONED SPEECH {holes}" if holes else ""))


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    bad = 0
    for mp4 in sys.argv[1:]:
        ok, msg = check(mp4)
        tag = "PASS" if ok else ("????" if ok is None else "FAIL")
        bad += 0 if ok else 1
        print(f"  [{tag}] {os.path.basename(mp4)[:52]:54} {msg}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
