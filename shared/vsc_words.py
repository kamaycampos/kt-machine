#!/usr/bin/env python3
"""Word-level timings for a WHOLE video, cached, built from short chunks.

Long windows corrupt both the words and the timestamps (measured 6 Sept), so the
whole file is transcribed 12 seconds at a time and stitched. One pass per video
makes every boundary lookup instant afterwards.
"""
import json, os, re, subprocess, sys

FFMPEG  = os.path.expanduser("~/Kamay/bin/ffmpeg")
WHISPER = os.path.expanduser("~/Kamay/whisper.cpp/build/bin/whisper-cli")
MODEL   = os.path.expanduser("~/Kamay/whisper.cpp/models/ggml-small.en.bin")
WORK    = os.path.expanduser("~/Desktop/VSC/.work")
CHUNK   = 12.0
# PRIMED TO PUNCTUATE - carried over from the KT pipeline, 16 Sept 2026.
# whisper only punctuates when primed with punctuation. Unprimed, two KT
# transcripts had 2 and 3 full stops in 39 and 51 minutes; primed, the same
# audio went 0% -> 75%. Clip EDGES are found from sentence boundaries, and
# edges are VSC's hardest problem, so this is the most useful change here.
# It only affects NEW transcriptions - nothing already delivered is touched.
PUNCT_PROMPT = ("Hello, everyone. Today, we are going to talk about money, health, and "
          "success. It is important, isn't it?")
FILLER  = re.compile(r"^(um|uh|erm|ah|mm|hmm)[,.!?]?$", re.I)


def norm(t):
    return re.sub(r"[^a-z0-9']", "", t.lower())


def build(src, base, dur):
    out = os.path.join(WORK, base + ".words.json")
    if os.path.exists(out):
        return json.load(open(out))
    words, t = [], 0.0
    n = 0
    while t < dur:
        b = min(t + CHUNK, dur)
        wav = "/tmp/vsc_w.wav"
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-ss", f"{t:.3f}", "-to", f"{b:.3f}",
                        "-i", src, "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", wav], check=True)
        # NEVER PROMPT THIS PASS. A punctuation prompt in `-ml 1 -sow` mode
        # COMPRESSES the timestamps: added 16 Sept, it drifted captions by up to
        # 9.5s across 7 clips before anyone noticed. Punctuation is worth having,
        # but it is taken from the separate normal-mode pass (vsc_v2caps), which
        # can be prompted safely. This pass is trusted for TIMES only.
        subprocess.run([WHISPER, "-m", MODEL, "-f", wav, "-ml", "1", "-sow", "-bs", "5",
                        "-oj", "-of", "/tmp/vsc_w"], capture_output=True)
        try:
            j = json.load(open("/tmp/vsc_w.json"))
        except Exception:
            j = {"transcription": []}
        span = b - t
        for s in j["transcription"]:
            txt = s["text"].strip()
            if not txt or FILLER.match(txt):
                continue
            wa = s["offsets"]["from"] / 1000.0
            wb = s["offsets"]["to"] / 1000.0
            if wa > span + 0.05:
                continue
            words.append({"t": txt, "n": norm(txt),
                          "a": round(t + wa, 3), "b": round(t + min(wb, span), 3)})
        t = b
        n += 1
        if n % 20 == 0:
            print(f"    {t:.0f}/{dur:.0f}s", flush=True)
    words = [w for w in words if w["n"]]
    json.dump(words, open(out, "w"))
    return words


if __name__ == "__main__":
    import glob
    sys.path.insert(0, os.path.expanduser("~/Kamay"))
    import vsc_edges as E
    for f in sorted(glob.glob(os.path.expanduser("~/Desktop/VSC/Source/*.mp4"))):
        base = os.path.splitext(os.path.basename(f))[0]
        dur = E.analyse(f, base)["dur"]
        print(f"=== {base[:44]} ({dur:.0f}s)", flush=True)
        w = build(f, base, dur)
        print(f"    {len(w)} words cached", flush=True)
    print("WORDSDONE")
