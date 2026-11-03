"""EXACT CAPTION TIMING: every word pinned to the moment its sound starts (3 Nov 2026).

Kamay, on the word-by-word captions: "the moment Kevin rushes talking, the CC does not keep up
with it ... IT NEEEEEDS TO BE THE EXACCCTTTT MOMENT ... IF NOT PEOPLE KNOW AND GET RESISTANCE AND
LEAVE." Then: "do anything necessary to make sure they are 100% dialed in."

He was right, and the cause is measurable. Our word times come from whisper, which GUESSES where
each word falls; anchor_words (vsc_v2_time) pins them where speech resumes after a pause, and in
between only interpolates. In Kevin's fast list on AN-ALIEN-ON-TV ("people aren't going to jump
out of buildings, people aren't going to start crying...") the words ran up to 0.68s late - the
pauses were right, everything between them drifted.

Forced alignment does not guess. It is handed the words (we already know them) and a speech
model finds where each LETTER sounds (wav2vec2, torchaudio). Checked against the level track at
every point he resumes after a breath: within 0.04s, where whisper was off by up to 0.68s.

Never trusted blind. The result is compared with the sound's own onsets (a rise out of quiet is a
fact about the audio, not a model's opinion); if the two disagree, the anchored times are kept
and the log says why. If torch is not installed, nothing changes. A caption polish never loses a
clip.

    words = kt_align.align(src, t_in, t_out, words)      # [(start, end, text)] in and out
"""
import os
import re
import subprocess
import sys

FF = os.path.expanduser("~/Kamay/bin/ffmpeg")
SR = 16000
CHUNK = 24.0          # seconds of speech per pass (attention memory grows with the square)
PAD = 1.0             # audio either side of a chunk: anchored times can be ~0.7s out
AGREE_MED = 0.08      # median distance to the sound's onsets above which the alignment is refused
AGREE_N = 4           # onsets needed before that verdict means anything
WILD = 1.5            # an aligned word this far from its anchored time is suspect...
WILD_SHARE = 0.20     # ...and this share of suspects refuses the whole clip
_MODEL = []

ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen " \
       "fifteen sixteen seventeen eighteen nineteen".split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def _say(n):
    """An integer as words - the model hears "five thousand", not "5,000"."""
    if n < 20:
        return ONES[n]
    if n < 100:
        return TENS[n // 10] + ("" if n % 10 == 0 else " " + ONES[n % 10])
    if n < 1000:
        return ONES[n // 100] + " hundred" + ("" if n % 100 == 0 else " " + _say(n % 100))
    for v, name in ((10 ** 12, "trillion"), (10 ** 9, "billion"), (10 ** 6, "million"), (1000, "thousand")):
        if n >= v:
            return _say(n // v) + " " + name + ("" if n % v == 0 else " " + _say(n % v))
    return ""


def spoken(w):
    """The letters a word is SAID with: '$5,000' -> 'FIVE THOUSAND DOLLARS', '20%' -> ..."""
    t = w.strip()
    out = []
    for tok in re.findall(r"\$?\d[\d,]*(?:\.\d+)?%?|[A-Za-z']+", t):
        m = re.fullmatch(r"(\$?)(\d[\d,]*)(?:\.(\d+))?(%?)", tok)
        if m:
            n = int(m.group(2).replace(",", "") or 0)
            s = _say(n) if n < 10 ** 15 else ""
            if m.group(3):
                s += " point " + " ".join(ONES[int(d)] for d in m.group(3))
            if m.group(4):
                s += " percent"
            if m.group(1):
                s += " dollars"
            out.append(s)
        else:
            out.append(tok)
    return re.sub(r"[^A-Z' ]", "", " ".join(out).upper()).split()


def _model():
    if not _MODEL:
        import torchaudio
        b = torchaudio.pipelines.WAV2VEC2_ASR_BASE_960H
        _MODEL.append((b.get_model().eval(), b.get_labels()))
    return _MODEL[0]


def _align_chunk(x, words, t0):
    """Align `words` inside audio `x` (which starts at clip time t0). [(start, end, score)] or None."""
    import torch
    import torchaudio
    model, labels = _model()
    idx = {c: i for i, c in enumerate(labels)}
    seq, owner = [], []                    # token -> the word it belongs to
    for k, w in enumerate(words):
        for part in spoken(w[2]):
            for c in part:
                if c in idx:
                    seq.append(idx[c]); owner.append(k)
            seq.append(idx["|"]); owner.append(-1)
    if seq and owner[-1] == -1:
        seq.pop(); owner.pop()
    if not seq:
        return None
    with torch.inference_mode():
        em, _ = model(torch.tensor(x)[None])
    em = torch.log_softmax(em, -1)
    if em.shape[1] < len(seq):
        return None
    ali, sc = torchaudio.functional.forced_align(em, torch.tensor([seq]), blank=0)
    spans = torchaudio.functional.merge_tokens(ali[0], sc[0].exp())
    per = len(x) / em.shape[1] / SR
    got = {}
    for sp, k in zip(spans, owner):
        if k < 0:
            continue
        a, b = t0 + sp.start * per, t0 + sp.end * per
        s0, e0, ss, n = got.get(k, (a, b, 0.0, 0))
        got[k] = (min(s0, a), max(e0, b), ss + float(sp.score), n + 1)
    return [(got[k][0], got[k][1], got[k][2] / got[k][3]) if k in got else None for k in range(len(words))]


def align(src, t_in, t_out, words, quiet=False):
    """[(start, end, text)] clip-relative in, the same with every start on its sound out."""
    if not words or os.environ.get("CAPTION_ALIGN", "1") == "0":
        return words
    try:
        import numpy as np
        import torch  # noqa: F401
        import torchaudio  # noqa: F401
    except ImportError:
        if not quiet:
            print("      caption timing: aligner not installed - anchored times kept")
        return words
    raw = subprocess.run([FF, "-loglevel", "error", "-ss", f"{t_in:.3f}", "-to", f"{t_out:.3f}", "-i", src,
                          "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0
    dur = len(x) / SR
    words = [tuple(w) for w in words]
    # chunks of whole words, cut where he pauses
    chunks, cur = [], []
    for k, w in enumerate(words):
        if cur and (w[0] - words[cur[0]][0] > CHUNK and w[0] - words[k - 1][1] > 0.12
                    or w[0] - words[cur[0]][0] > CHUNK + 8):
            chunks.append(cur); cur = []
        cur.append(k)
    if cur:
        chunks.append(cur)
    out = [None] * len(words)
    for ch in chunks:
        a = max(0.0, words[ch[0]][0] - PAD)
        b = min(dur, words[ch[-1]][1] + PAD)
        r = _align_chunk(x[int(a * SR):int(b * SR)], [words[k] for k in ch], a)
        if r:
            for k, v in zip(ch, r):
                out[k] = v
    # words the model could not place (no letters) sit between their neighbours
    if sum(1 for v in out if v) < max(2, len(words) // 2):
        if not quiet:
            print("      caption timing: alignment found too few words - anchored times kept")
        return words
    res = []
    for k, w in enumerate(words):
        if out[k]:
            s, e = out[k][0], max(out[k][1], out[k][0] + 0.06)
        else:
            lo = max((j for j in range(k) if out[j]), default=None)
            hi = min((j for j in range(k + 1, len(words)) if out[j]), default=None)
            s = out[lo][1] if lo is not None else max(0.0, out[hi][0] - 0.2)
            e = out[hi][0] if hi is not None else s + 0.3
            e = max(e, s + 0.06)
        res.append((round(s, 3), round(e, 3), w[2]))
    for k in range(1, len(res)):                       # never out of order
        if res[k][0] < res[k - 1][0]:
            res[k] = (res[k - 1][0], max(res[k][1], res[k - 1][0] + 0.06), res[k][2])
    # THE SOUND REFEREES. Where speech rises out of quiet, the word starting there must start there.
    try:
        sys.path.insert(0, os.path.expanduser("~/Kamay"))
        import vsc_v2_time
        ons = vsc_v2_time.onsets(vsc_v2_time.envelope(src, t_in, t_out))
    except Exception:
        ons = []
    starts = [r[0] for r in res]
    errs = []
    for t in ons:
        d = min((s - t for s in starts), key=abs, default=None)
        if d is not None and abs(d) <= 0.25:
            errs.append(abs(d))
    errs.sort()
    med = errs[len(errs) // 2] if errs else None
    wild = sum(1 for r, w in zip(res, words) if abs(r[0] - w[0]) > WILD)
    if len(errs) >= AGREE_N and med > AGREE_MED:
        if not quiet:
            print(f"      caption timing: alignment REFUSED - {med:.2f}s from the sound's onsets "
                  f"(n={len(errs)}); anchored times kept")
        return words
    # Only when the sound has too few onsets to referee do the old times get a vote. On AN-ALIEN-ON-TV
    # the anchored times were themselves 1.9s late (a repeated phrase pinned to the wrong line) and
    # this guard, trusted over the onsets, refused the alignment that was right to 0.02s.
    if len(errs) < AGREE_N and wild > WILD_SHARE * len(words):
        if not quiet:
            print(f"      caption timing: alignment REFUSED - {wild} of {len(words)} words moved over "
                  f"{WILD}s; anchored times kept")
        return words
    if not quiet:
        moved = sorted(abs(r[0] - w[0]) for r, w in zip(res, words))
        print(f"      caption timing: {len(res)} words force-aligned; onsets agree within "
              f"{'-' if med is None else f'{med:.2f}s'} (n={len(errs)}); moved median "
              f"{moved[len(moved) // 2]:.2f}s, worst {moved[-1]:.2f}s")
    return res
