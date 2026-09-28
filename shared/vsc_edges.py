#!/usr/bin/env python3
"""Clip boundaries taken from the WAVEFORM, and who is speaking.

6 Sept. Kamay watched all 19 clips: "almost every single clip ends either when KT
is still talking or when the interviewer is asking a question and some of them
starts mid sentence. this is unacceptable."

My error was validating that the TRANSCRIPT TEXT ended in a full stop. That is
not the same as the audio stopping, and this transcript was already proven
inaccurate (it placed one sentence end 0.34s early and mis-heard whole phrases).
It also carries the interviewer's speech with no speaker labels at all.

So boundaries come from the audio now:
  * a clip may only END at a real silence gap, and START just after one
  * spans are attributed to a speaker by pitch, and a clip may contain only Kevin
"""
import json, os, subprocess, wave, audioop, math
import numpy as np

FFMPEG   = os.path.expanduser("~/Kamay/bin/ffmpeg")
WORK     = os.path.expanduser("~/Desktop/VSC/.work")
FRAME    = 0.02          # 20ms analysis frame
MIN_GAP  = 0.34          # a confident sentence break
FINE_GAP = 0.18          # fallback: Kevin can run 100s+ without a 0.34s pause          # a real breath/sentence break, not a plosive
MIN_SPAN = 0.45          # ignore blips


def _pcm(src, t0=None, t1=None):
    cmd = [FFMPEG, "-y", "-loglevel", "error"]
    if t0 is not None: cmd += ["-ss", str(t0)]
    if t1 is not None: cmd += ["-to", str(t1)]
    tmp = "/tmp/vsc_edge.wav"
    cmd += ["-i", src, "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", tmp]
    subprocess.run(cmd, check=True)
    w = wave.open(tmp); raw = w.readframes(w.getnframes()); w.close(); os.remove(tmp)
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32)


def analyse(src, base):
    """Speech spans separated by real silence. Cached; the decode is the slow part.

    Pitch-based speaker separation was tried on 6 Sept and REJECTED - it labelled
    Kevin's own control regions as another speaker. The interviewer is identified
    from the transcript instead (see INTERVIEWER in vsc_plan.py).
    """
    out = os.path.join(WORK, base + ".edges.json")
    if os.path.exists(out) and json.load(open(out)).get("v") == 3:
        return json.load(open(out))
    x = _pcm(src)
    step = int(16000 * FRAME)
    rms = np.array([np.sqrt(np.mean(x[i:i+step] ** 2) + 1e-9)
                    for i in range(0, len(x) - step, step)])
    db = 20 * np.log10(rms + 1e-9)
    floor, peak = np.percentile(db, 10), np.percentile(db, 95)
    thr = floor + (peak - floor) * 0.30
    voiced = db > thr
    def build(min_gap):
        spans, i, n = [], 0, len(voiced)
        need = int(min_gap / FRAME)
        while i < n:
            if not voiced[i]: i += 1; continue
            j = i
            while j < n:
                if voiced[j]: j += 1; continue
                k = j
                while k < n and not voiced[k]: k += 1
                if k - j >= need: break
                j = k
            spans.append([round(i * FRAME, 3), round(min(j, n) * FRAME, 3)])
            i = j
        return [s for s in spans if s[1] - s[0] >= MIN_SPAN]

    data = {"v": 3, "spans": build(MIN_GAP), "fine": build(FINE_GAP),
            "dur": round(len(x) / 16000.0, 2)}
    json.dump(data, open(out, "w"))
    return data
