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


WH = os.path.expanduser("~/Kamay/whisper.cpp/build/bin/whisper-cli")
WM = os.path.expanduser("~/Kamay/whisper.cpp/models/ggml-small.en.bin")


def _norm(w):
    return re.sub(r"[^a-z0-9']", "", w.lower())


def fill_missing(x, words):
    """Add the words the timing pass never heard. ([words], {indices added})

    3 Nov 2026, HE-SKIPPED-A-430K-MAYBACH: the factory refused it for "UNCAPTIONED SPEECH
    97.0-99.3" - Kevin says "And I drive..." and the one-word-per-line pass that supplies our
    words (whisper -ml 1) had dropped it, along with "back then", "the car off", "didn't
    happen". That pass is kept for its clock; it is the worse listener. A normal-mode pass over
    the clip (windows cut in the middle of his pauses, so no word is split) hears them; the two
    are compared ONCE over the whole clip, and only what it adds BETWEEN words we already have
    is taken (a pure insertion) - never a rewrite of words we have (only their punctuation and
    sentence capitals, see merge_heard). The aligner then places the new words on their sound,
    and one it cannot find in the audio is dropped again (align)."""
    import difflib
    import tempfile
    import wave
    dur = len(x) / SR
    cuts, last = [0.0], 0.0
    for k in range(1, len(words)):
        gap = words[k][0] - words[k - 1][1]
        mid = (words[k - 1][1] + words[k][0]) / 2
        if (gap >= 0.3 and mid - last > 15) or mid - last > 28:
            cuts.append(mid); last = mid
    cuts.append(dur)
    heard, edge = [], set()          # edge: heard indices at the cut between two windows
    tmp = os.path.join(tempfile.gettempdir(), f"kt_fill_{os.getpid()}.wav")
    for a, b in zip(cuts, cuts[1:]):
        if b - a < 0.4:
            continue
        seg = (x[int(a * SR):int(b * SR)] * 32767).astype("int16")
        with wave.open(tmp, "wb") as f:
            f.setnchannels(1); f.setsampwidth(2); f.setframerate(SR); f.writeframes(seg.tobytes())
        r = subprocess.run([WH, "-m", WM, "-f", tmp, "-bs", "5", "-nt"], capture_output=True, text=True)
        got = [h for h in re.sub(r"\[.*?\]|\(.*?\)", " ", r.stdout).split() if _norm(h)]
        if got:
            if heard:
                edge.update((len(heard) - 1, len(heard)))
            heard += got
    try:
        os.remove(tmp)
    except OSError:
        pass
    return merge_heard(words, heard, edge)


_END = (".", "!", "?")
_PUNCT = (".", "!", "?", ",", ";", ":")
_PROPER = {"i", "i'm", "i've", "i'll", "i'd", "god", "kevin", "trudeau", "america", "american"}
try:
    from kt_qc import STARTERS as _STARTERS          # the words kt_qc reads as a sentence start
except Exception:
    _STARTERS = {"the", "this", "that", "these", "we", "you", "they", "he", "she", "it", "and", "but",
                 "so", "guess", "now", "what", "if", "because", "there", "well", "look", "every", "most",
                 "without", "when", "successful", "people"}


def _tail(w):
    m = re.search(r"[.!?,;:]+$", w.rstrip("\"'’”"))
    return m.group(0) if m else ""


def merge_heard(words, heard, edge=()):
    """The timing pass's words, with the normal-mode pass's added words AND its sentences.

    4 Nov 2026, why KT queued nothing for a day [Certain, GLASS-BRIDGE's caption record]: our
    words come from the one-word-per-line pass (whisper -ml 1), which keeps time but writes almost
    no full stops and almost no capitals ("close your eyes hi I'm guru joe so and I am gonna"). The
    old looks passed kt_qc only because nothing was capitalised, so the missing stops were
    invisible. The missed-word fill takes words from the normal-mode pass, which writes "He",
    "The", "Because" with a capital - next to a word that never got its stop: "It's awesome He",
    "happen The", "now He"; and a stutter it heard ("It's it's", "the the") came in as a repeat.
    Twelve kt_qc faults on one clip, in cinema as much as in look E.

    So the normal-mode pass, the better listener, also lends its SENTENCES: where it matches our
    word, its trailing punctuation and its sentence-start capital are carried across (times
    never). Except at the cut between two of its windows: whisper ends every window with a stop
    and opens the next with a capital, true or not. A stutter is never added. And a capital still
    standing with no stop before it is a casing slip, not a sentence: lower case, as the old
    captions always were. Returns ([words], {indices added})."""
    import difflib
    words = [tuple(w) for w in words]
    hn = [_norm(h) for h in heard]
    sm = difflib.SequenceMatcher(a=[_norm(w[2]) for w in words], b=hn, autojunk=False)
    ops = sm.get_opcodes()

    def sent_start(j):                 # heard[j] opens a sentence in the normal-mode text
        return j > 0 and j not in edge and j - 1 not in edge and heard[j - 1].endswith(_END)

    def lend(w, j, last=False):
        """Our word w, with heard[j]'s punctuation and sentence-start casing."""
        h = heard[j]
        t = _tail(h)
        # a stop at a window's edge is whisper closing the window, not him ending a sentence -
        # except the very end of the clip, which IS where he finishes
        if t and not _tail(w) and (j not in edge or t[0] not in _END or last):
            w = w + t
        core = re.sub(r"[^A-Za-z']", "", w)
        if core and sent_start(j) and h[:1].isupper() and w[:1].islower():
            w = w[:1].upper() + w[1:]
        elif core and w[:1].isupper() and h[:1].islower() and _norm(w) not in _PROPER:
            w = w[:1].lower() + w[1:]
        return w

    words = list(words)
    before = [w[2] for w in words]
    for tag, i1, i2, j1, j2 in ops:
        if tag == "equal":
            for i, j in zip(range(i1, i2), range(j1, j2)):
                a, b, w = words[i]
                words[i] = (a, b, lend(w, j, last=(j == len(heard) - 1)))
    ins = {}
    for tag, i1, _i2, j1, j2 in ops:
        if tag != "insert" or not (0 < i1 < len(words)) or j2 - j1 > 6:
            continue
        new = []
        for j in range(j1, j2):
            h = heard[j]
            prev = hn[j - 1] if j > j1 else _norm(words[i1 - 1][2])
            nxt = hn[j + 1] if j + 1 < j2 else _norm(words[i1][2])
            # A STUTTER IS NOT A MISSED WORD: "it's, it's" / "the the" read as damage on screen and
            # kt_qc refuses it. Only a word the timing pass truly lost is worth adding.
            if hn[j] in (prev, nxt):
                continue
            if h[:1].isupper() and not sent_start(j) and hn[j] not in _PROPER and h[1:2].islower():
                h = h[:1].lower() + h[1:]
            new.append(h)
        if not new:
            continue
        ins[i1] = new
        # THE FULL STOP COMES WITH THE WORD (4 Nov 2026): where an insertion opens a sentence, the
        # word before it ends one ("awesome. He").
        if j1 > 0 and j1 - 1 not in edge and heard[j1 - 1].endswith(_END):
            a, b, w = words[i1 - 1]
            if not _tail(w):
                words[i1 - 1] = (a, b, w + heard[j1 - 1][-1])
    stopped = {i for i, w in enumerate(words) if w[2].endswith(_END) and not _tail(before[i])}
    out, added, stop_at = [], set(), set()
    for i, w in enumerate(words):
        if i in ins:
            lo, hi = words[i - 1][1], w[0]
            step = max(hi - lo, 0.06 * len(ins[i])) / (len(ins[i]) + 1)
            for n, h in enumerate(ins[i], 1):
                added.add(len(out))
                out.append((round(lo + n * step, 3), round(lo + n * step + 0.05, 3), h))
        if i in stopped:
            stop_at.add(len(out))
        out.append(w)
    # a stop we carried ends a sentence, so the next word opens one (never "the number. one")
    # ...and so does a word the fill adds right after a stop the timing pass already had
    stop_at |= {k - 1 for k in added if k > 0 and out[k - 1][2].rstrip("\"'\u2019\u201d").endswith(_END)
                and not out[k - 1][2].endswith("...")}
    for k in sorted(stop_at):
        if k + 1 < len(out) and out[k + 1][2][:1].islower():
            a, b, w = out[k + 1]
            out[k + 1] = (a, b, w[:1].upper() + w[1:])
    # A CAPITAL WITH NO STOP BEFORE IT IS A CASING SLIP ("gonna Build this", "and Then I"): neither
    # pass put a sentence there, so it reads the way every caption before 3 Nov did - lower case.
    for k in range(1, len(out)):
        a, b, w = out[k]
        if (w[:1].isupper() and w[1:2].islower() and _norm(w) in _STARTERS
                and not out[k - 1][2].rstrip("\"'’”").endswith(_PUNCT + ("-",))):
            out[k] = (a, b, w[:1].lower() + w[1:])
    return out, added


def _chunks(words):
    """Whole words, cut where he pauses, about CHUNK seconds each."""
    chunks, cur = [], []
    for k, w in enumerate(words):
        if cur and (w[0] - words[cur[0]][0] > CHUNK and w[0] - words[k - 1][1] > 0.12
                    or w[0] - words[cur[0]][0] > CHUNK + 8):
            chunks.append(cur); cur = []
        cur.append(k)
    if cur:
        chunks.append(cur)
    return chunks


def align(src, t_in, t_out, words, quiet=False, fill=True):
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
    added = set()
    # fill=False: VSC's text is read and corrected word for word before timing (capread), so
    # there only the clock moves - never the words.
    if fill and os.environ.get("CAPTION_FILL", "1") != "0" and os.path.exists(WH):
        try:
            words, added = fill_missing(x, words)
        except Exception as e:                       # a missed word is better than a lost clip
            sys.stderr.write(f"      caption fill skipped: {type(e).__name__}: {e}\n")
    chunks = _chunks(words)
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
    # AN ADDED WORD THE SOUND DOES NOT CARRY IS DROPPED: the model crushes it to nothing (or onto
    # its neighbour) when it is not there - a normal-mode hallucination, not something he said.
    if added:
        keep = [k for k in range(len(res)) if k not in added or (
            out[k] and res[k][1] - res[k][0] >= 0.06 and out[k][2] >= 0.30
            and (k == 0 or abs(res[k][0] - res[k - 1][0]) >= 0.03))]
        if not quiet:
            print(f"      caption timing: {len(added)} word(s) the timing pass missed, "
                  f"{sum(1 for k in keep if k in added)} confirmed by the sound and captioned")
        res = [res[k] for k in keep]
        words = [words[k] for k in keep]
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
