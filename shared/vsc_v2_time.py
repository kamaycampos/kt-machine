#!/usr/bin/env python3
"""Pin every caption to the moment the sound actually starts.

23 Sept 2026, Kamay on the revised 29: "I want the word to match to his mouth -
whenever he is saying a word that word already needs to be on the screen, not
before he says it or after."

Measured first, on CONFRONT-IT-VANISHES: at every point where Kevin resumes after
a pause, the captions were a mean of +0.25s LATE and up to +1.25s late. whisper's
word clock drifts locally and a second whisper run cannot referee the first one
(two runs on identical audio disagreed by 0.39s, 16 Sept). The waveform can: a
rise out of silence is a fact about the sound, not an opinion about the words.

  ANCHOR  every word that follows a real gap in our own timeline is matched to the
          nearest sound onset within 0.40s. Monotonic, one onset per word, so a
          mispaired anchor cannot drag the rest.
  WARP    times between two anchors are stretched linearly. Drift cannot cross an
          anchor.
  NO LEAD The caption starts exactly where the sound does. A 0.08s head start
          was tried and removed on 23 Sept: it left the previous caption's end
          untouched, so both were drawn at once for two frames at every change.

Onsets are measured against a threshold taken per 60s block, never a constant:
a fixed -30dB went deaf on a stretch with a -32dB noise floor (10 Sept) and
failed silently.
"""
import difflib, json, os, re, subprocess, sys
import numpy as np
sys.path.insert(0, os.path.expanduser("~/Kamay"))
import kt_render                                                 # noqa: E402

FF = os.path.expanduser("~/Kamay/bin/ffmpeg")
WORK = os.path.expanduser("~/Desktop/VSC/.work")
CAPS = os.path.join(WORK, "v2caps")
HOP = 0.010
GAP_MIN = 0.18      # a gap in our timeline big enough that the sound should show one
NEAR = 0.40         # never pull a word further than this: past it, it is a guess


def envelope(src, a, b):
    raw = subprocess.run([FF, "-y", "-loglevel", "error", "-ss", f"{a:.3f}", "-to", f"{b:.3f}",
                          "-i", src, "-ar", "16000", "-ac", "1", "-f", "s16le", "-"],
                         capture_output=True).stdout
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
    st = int(16000 * HOP)
    n = len(x) // st
    rms = np.sqrt(np.array([np.mean(x[i * st:(i + 1) * st] ** 2) for i in range(n)]) + 1e-9)
    return 20 * np.log10(rms + 1e-9)


def onsets(db):
    """Times where sound rises out of quiet. Threshold per 60s block, not a constant."""
    blk = int(60 / HOP)
    thr = np.empty_like(db)
    for i in range(0, len(db), blk):
        s = db[i:i + blk]
        # IGNORE DIGITAL SILENCE WHEN MEASURING THE FLOOR. 27 Sept: LAUGH-NOW has
        # frames at -90dB (true zero, not room tone), which dragged the 12th
        # percentile down so far that the threshold sat at -30dB and the detector
        # went deaf: 10 onsets in 49 seconds, an 11-second gap with none at all, and
        # the captions in those gaps drifted over a second behind him. The threshold
        # has to track the ROOM, so the floor is measured from frames that actually
        # contain something. Same failure as the -30dB constant on 10 Sept, wearing
        # a different hat.
        real = s[s > -75]
        if real.size < max(8, s.size // 20):
            real = s
        lo, hi = np.percentile(real, 12), np.percentile(real, 92)
        thr[i:i + blk] = lo + (hi - lo) * 0.38
    out, quiet = [], 10
    for i in range(len(db)):
        if db[i] <= thr[i]:
            quiet += 1
            continue
        if quiet >= 8 and all(db[k] > thr[k] for k in range(i, min(i + 3, len(db)))):
            out.append(i * HOP)
        quiet = 0
    return out


def anchor(words, ons):
    """[(index, true_time)] - each sound onset matched to the word it starts.

    Driven from the ONSETS, not from gaps in our own timeline: in `-ml 1 -sow`
    mode whisper hands every word an end time that runs into the next word's
    start, so asking "which of our words follows a pause" found 1-11 places in a
    whole clip. The sound knows where the pauses are; our clock does not.

    Monotonic and one-to-one, so a wrong pairing stays local: an onset may only
    take a word later than the one already taken, and never one more than NEAR
    away - past that it would be a guess, and a guessed anchor is worse than none.
    """
    starts = [w[0] for w in words]
    pts, used = [], -1
    for t in ons:
        cand = [i for i in range(used + 1, len(starts)) if abs(starts[i] - t) <= NEAR]
        if not cand:
            continue
        i = min(cand, key=lambda i: abs(starts[i] - t))
        pts.append((i, t))
        used = i
    # NO SECOND, WIDER SWEEP. Tried 23 Sept at 0.75s for the onsets no word
    # claimed, to catch drift past the last anchor: it moved 17 of 29 clips and
    # dragged PAPER-TIGER's ending 1.4s LATE, off words that had been sitting
    # exactly on the sound (107.77, 108.07, 109.44). Anchoring runs three times,
    # so one loose pairing shifts the timeline and lets the next pass pair things
    # that were never close. A looser rule is not a safer rule.
    return drop_impossible(pts, starts)


def drop_impossible(pts, starts):
    """Throw away any anchor that would demand an impossible change of speed.

    Nearest-onset pairing is only as good as the word list: if whisper dropped a
    word, an onset can latch onto its neighbour and drag everything between two
    anchors with it. That shows up as a stretch - the sound says a phrase took
    half as long as our clock does. Nobody speaks 40% faster for one phrase and
    normal again straight after, so a span whose speed ratio falls outside
    [0.7, 1.4] is a mispairing, and the anchor that the neighbouring spans agree
    less with is dropped.
    """
    ok = list(pts)
    for _ in range(len(pts)):
        bad = None
        for k in range(len(ok) - 1):
            (i1, t1), (i2, t2) = ok[k], ok[k + 1]
            ours, true = starts[i2] - starts[i1], t2 - t1
            if ours < 0.25 or true < 0.25:
                continue
            r = true / ours
            if r < 0.7 or r > 1.4:
                bad = k if k == 0 else (k + 1 if k + 1 == len(ok) - 1 else
                                        (k if abs(ok[k][1] - starts[ok[k][0]]) >
                                         abs(ok[k + 1][1] - starts[ok[k + 1][0]]) else k + 1))
                break
        if bad is None:
            break
        ok.pop(bad)
    return ok


def warp_times(words, pts):
    if len(pts) < 2:
        return words, 0.0
    ours = [words[i][0] for i, _ in pts]
    true = [t for _, t in pts]
    def m(t):
        if t <= ours[0]:
            return t + (true[0] - ours[0])
        if t >= ours[-1]:
            return t + (true[-1] - ours[-1])
        for (o1, t1), (o2, t2) in zip(zip(ours, true), zip(ours[1:], true[1:])):
            if o1 <= t <= o2:
                return t1 + (t - o1) * ((t2 - t1) / (o2 - o1) if o2 > o1 else 1.0)
        return t
    moved = max(abs(o - t) for o, t in zip(ours, true))
    return [(round(m(s), 3), round(max(m(e), m(s) + 0.06), 3), w) for s, e, w in words], moved


MAX_EARLY = 0.85     # no word may sit on screen longer than this before it is said
SPLIT_GAP = 0.35     # a pause inside a burst is a place to break, not to sit through
MIN_SHOW = 0.50      # ...unless the piece left behind is too brief to read


def words_per_burst(bursts, words):
    """The words each caption is made of - taken from its TEXT, never its span.

    A burst's end time is stretched to the start of the next one (so a pause does
    not blank the screen), which means a time window around a caption also catches
    the words of the caption AFTER it. Measuring "how early is this word shown"
    that way blamed captions for words they do not contain - and splitting on it
    put the next caption's first word into this one ("go" / "crazy. One").
    """
    out, i = [], 0
    for _s, _e, t in bursts:
        want = "".join(re.sub(r"[^a-z0-9]", "", x.lower()) for x in t.split())
        grp, acc = [], ""
        while i < len(words) and len(acc) < len(want):
            grp.append(words[i])
            acc += re.sub(r"[^a-z0-9]", "", words[i][2].lower())
            i += 1
        if acc != want:                 # numbers_to_digits rewrote a word: fall back
            n = len(t.split())
            i = i - len(grp) + n
            grp = words[max(0, i - n):i]
        out.append(grp)
    return out


def split_early(bursts, words):
    """Break a caption ONLY where a word would otherwise sit waiting to be said.

    The captions as submitted were already good on this - 1.9% of words showed
    more than 0.9s early. So this does not second-guess where phrases_from_words
    chose to break; it steps in only when a word in a caption would be on screen
    more than MAX_EARLY before Kevin says it, and then only at a break that
    scorer would itself accept: after punctuation or a real pause, never ending on
    an article or a weak word, never between two words that are one thought.

    A first version split on every pause and produced "Growing / up," - the exact
    break reviewers have flagged before ("NEW / YORK"). Timing is not worth a
    worse line.

    Splitting costs nothing on screen: a burst is held until the next one starts
    whenever the gap is under 1.5s, so the frame never blanks.
    """
    WEAK = ("the", "a", "an", "my", "your", "his", "her", "our", "their", "this",
            "and", "or", "of", "to", "in", "on", "at", "for", "but", "so", "that",
            "is", "was", "are", "were", "be", "been", "it's", "i'm")

    def can_break(g, k):
        prev, nxt = g[k - 1][2].strip(), g[k][2].strip()
        gap = g[k][0] - g[k - 1][1]
        if not (prev.endswith((".", "!", "?", ",", ":", ";")) or gap >= 0.30):
            return False
        if prev.lower().strip(".,!?\"'") in WEAK and not prev.endswith((".", "!", "?")):
            return False
        if (prev.lower().strip(".,!?\"'"), nxt.lower().strip(".,!?\"'")) in kt_render.TOGETHER:
            return False
        pc, nc = prev.strip("\"'(,"), nxt.strip("\"'(,")
        if (pc[:1].isupper() and nc[:1].isupper() and nc not in ("I", "I'm", "I've", "I'll", "I'd")
                and not prev.endswith((".", "!", "?"))):
            return False                      # a name: New York, Harvard Yard
        return True

    out, groups, cut = [], words_per_burst(bursts, words), 0
    for (s0, e0, t0), ws in zip(bursts, groups):
        pieces, stack = [], [ws] if len(ws) > 1 else [[w] for w in ws] or [[]]
        while stack:
            g = stack.pop(0)
            if len(g) < 2 or max(w[0] - g[0][0] for w in g) <= MAX_EARLY:
                pieces.append(g); continue
            ok = [k for k in range(1, len(g)) if can_break(g, k)
                  and (g[k][0] - g[0][0]) >= MIN_SHOW and (g[-1][1] - g[k][0]) >= MIN_SHOW]
            if not ok:
                pieces.append(g); continue
            # the break that leaves the least waiting on either side
            k = min(ok, key=lambda k: max(max(w[0] - g[0][0] for w in g[:k]),
                                          max(w[0] - g[k][0] for w in g[k:])))
            stack = [g[:k], g[k:]] + stack
            cut += 1
        for g in pieces:
            if g:
                out.append((round(g[0][0], 3), round(g[-1][1], 3), " ".join(w[2] for w in g)))
            elif t0:
                out.append((s0, e0, t0))
    out.sort()
    for i in range(len(out) - 1):          # keep the hold rule from phrases_from_words
        if out[i + 1][0] - out[i][1] < 1.5:
            out[i] = (out[i][0], out[i + 1][0], out[i][2])
    return out


def retime(name, src, a, b, report=True):
    P = os.path.join(CAPS, name + ".json")
    d = json.load(open(P))
    words = [tuple(w) for w in d["words"]]
    wav = "/tmp/v2retime.wav"
    subprocess.run([FF, "-y", "-loglevel", "error", "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", src,
                    "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", wav], check=True)
    ons = onsets(envelope(src, a, b))
    pts = anchor_by_identity(wav, words, ons)
    errs = [words[i][0] - t for i, t in pts]
    words2 = warp_by_index(words, pts)
    d["anchors"], d["unmatched_onsets"] = len(pts), len(ons) - len(pts)
    bursts = split_early(kt_render.phrases_from_words(words2), words2)
    # EVERY CAPTION ENDS WHERE THE NEXT ONE BEGINS. 23 Sept, Kamay: "this new
    # caption style is not good ... it is harder to read." A 0.08s head start had
    # been added to each caption's START while the one before it kept its old END,
    # so at all 2,024 caption changes in the 29 clips BOTH captions were drawn, on
    # top of each other, for two frames. There is no head start now either: he
    # asked for the word on screen when he says it, not before.
    bursts = [(s0, (bursts[k + 1][0] if k + 1 < len(bursts) else e0), t0)
              for k, (s0, e0, t0) in enumerate(bursts)]
    d["words"], d["bursts"] = words2, bursts
    if d.get("close_end") is not None:
        ci = min(range(len(words)), key=lambda i: abs(words[i][1] - d["close_end"]))
        d["close_end"] = words2[ci][1]
    json.dump(d, open(P, "w"), indent=0)
    if report:
        if errs:
            se = sorted(errs, key=abs)
            print(f"  {name:30} {len(pts):3d} anchors of {len(ons):3d} sounds  |  words were off by "
                  f"median {abs(se[len(se)//2]):.2f}s, worst {max(errs, key=abs):+.2f}s", flush=True)
        else:
            print(f"  {name:30} NO ANCHORS - left alone", flush=True)
    return len(pts), errs


# ---------------------------------------------------------------------------
# 23 Sept 2026, second round. Kamay: "in the breath of fire video the captions
# again come before KT says it, for example the word 'prison' comes before and
# then he says it."
#
# He is right, and it is not the warp: the ORIGINAL word pass already had
# "prison" at 6.06s when he says it at 8.13s. Kevin hesitates there - "to, uh,
# uh, my ultimate prison" - and whisper, reading 117 seconds in one go,
# compresses filled pauses and hands every following word a time that is up to
# two seconds early. Anchoring cannot rescue that: a word 2s adrift is nowhere
# near the onset it belongs to, so it gets pinned to the WRONG onset and the
# error is locked in.
#
# The same audio read in a SHORT window comes back correct (prison at 8.13).
# So the timing pass is now run over chunks cut at silences, never the whole
# clip. Text is not touched - only times are transferred onto the words that
# were already read and corrected.
# ---------------------------------------------------------------------------
WH = os.path.expanduser("~/Kamay/whisper.cpp/build/bin/whisper-cli")
MD = os.path.expanduser("~/Kamay/whisper.cpp/models/ggml-small.en.bin")
CHUNK = 12.0
MAX_PULL = 4.0      # whisper's clock drifts seconds, never a dozen: past this it is a mispairing
COMMON = {"and", "the", "a", "an", "to", "of", "in", "is", "it", "that", "this", "so", "but",
          "you", "i", "he", "she", "we", "they", "was", "were", "be", "for", "on", "at", "with"}


def _silences(wav):
    r = subprocess.run([FF, "-i", wav, "-af", "silencedetect=noise=-33dB:d=0.20", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    st = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", r)]
    en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r)]
    return [( (s + e) / 2 ) for s, e in zip(st, en) if e > s]


def timed_words_chunked(src, a, b):
    """[(start, end, word)] clip-relative, from SHORT windows cut at silences."""
    import kt_words
    wav = "/tmp/v2chunk_all.wav"
    subprocess.run([FF, "-y", "-loglevel", "error", "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", src,
                    "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", wav], check=True)
    span = b - a
    quiet = _silences(wav)
    cuts, t = [0.0], 0.0
    while t + CHUNK < span:
        near = [q for q in quiet if t + CHUNK * 0.55 < q < t + CHUNK * 1.45]
        t = near[len(near) // 2] if near else t + CHUNK
        cuts.append(round(t, 3))
    cuts.append(span)
    out = []
    for p, q in zip(cuts, cuts[1:]):
        if q - p < 0.4:
            continue
        subprocess.run([FF, "-y", "-loglevel", "error", "-ss", f"{p:.3f}", "-to", f"{q:.3f}",
                        "-i", wav, "-c:a", "pcm_s16le", "/tmp/v2chunk.wav"], check=True)
        subprocess.run([WH, "-m", MD, "-f", "/tmp/v2chunk.wav", "-ml", "1", "-sow", "-osrt",
                        "-of", "/tmp/v2chunk"], capture_output=True)
        try:
            for s, e, w in kt_words.parse_word_srt("/tmp/v2chunk.srt"):
                if w.strip():
                    out.append((round(p + s, 3), round(p + e, 3), w))
        except Exception:
            pass
    return out


def transfer_times(words, heard):
    """Put the chunked TIMES onto our words. Text is never changed."""
    hn = [re.sub(r"[^a-z0-9']", "", w[2].lower()) for w in heard]
    on = [re.sub(r"[^a-z0-9']", "", w[2].lower()) for w in words]
    fixed = [None] * len(words)
    for tag, i1, i2, j1, _j2 in difflib.SequenceMatcher(a=hn, b=on, autojunk=False).get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                fixed[j1 + k] = (heard[i1 + k][0], heard[i1 + k][1])
    known = [i for i, f in enumerate(fixed) if f]
    if len(known) < 2:
        return words, 0
    out = []
    for i, (s, e, w) in enumerate(words):
        if fixed[i]:
            out.append((fixed[i][0], max(fixed[i][1], fixed[i][0] + 0.06), w)); continue
        lo = max([k for k in known if k < i], default=None)
        hi = min([k for k in known if k > i], default=None)
        if lo is None:
            d = fixed[hi][0] - words[hi][0]
        elif hi is None:
            d = fixed[lo][0] - words[lo][0]
        else:                                   # stretch between the two known words
            os_, oe = words[lo][0], words[hi][0]
            ns, ne = fixed[lo][0], fixed[hi][0]
            r = (ne - ns) / (oe - os_) if oe > os_ else 1.0
            out.append((round(ns + (s - os_) * r, 3), round(ns + (e - os_) * r, 3), w)); continue
        out.append((round(s + d, 3), round(e + d, 3), w))
    out = sorted(out, key=lambda x: x[0])
    return [(s, max(e, s + 0.06), w) for s, e, w in out], len(known)


def _same(a, b):
    """Near enough to be the same word. whisper writes "Lincoln's" where the
    caption says "Lincolns", and an exact test scored that onset 1 instead of 2,
    so the anchor was skipped and Kevin's fast list of cars ran half a second
    late. Spelling is not the question here - position is."""
    if a == b:
        return True
    if abs(len(a) - len(b)) > 3 or min(len(a), len(b)) < 3:
        return False
    return difflib.SequenceMatcher(a=a, b=b).ratio() >= 0.8


def anchor_by_identity(wav, words, ons, last_free=25):
    """[(index, true_time)] - anchored by WHICH WORD is heard at each onset.

    Nearest-in-time pairing assumes our clock is already within 0.40s of the
    truth. Where Kevin hesitates it is not: "to, uh, uh, my ultimate prison" put
    every following word up to 2s early, so "prison" was pinned to an onset two
    words too early and the error was locked in - the defect Kamay spotted on
    BREATH-OF-FIRE. Time cannot referee time.

    So each onset is READ: a 1.4s window from it is transcribed in normal mode,
    and the words heard are matched against our list, searching forward from the
    last anchor. A short window does not drift (the same audio read whole put
    "prison" at 6.03s; read from 8.08s it says "prison" first, which is the truth).
    An onset whose words are not found just ahead of the last anchor is skipped:
    silence, music and b-roll claim nothing.
    """
    def nm(w):
        return re.sub(r"[^a-z0-9']", "", w.lower())
    on = [nm(w[2]) for w in words]
    pts, at = [], 0
    for t in ons:
        subprocess.run([FF, "-y", "-loglevel", "error", "-ss", f"{max(0.0, t - 0.05):.3f}",
                        "-t", "1.4", "-i", wav, "-c:a", "pcm_s16le", "/tmp/v2on.wav"], check=True)
        r = subprocess.run([WH, "-m", MD, "-f", "/tmp/v2on.wav", "-bs", "5", "-nt"],
                           capture_output=True, text=True).stdout
        heard = [nm(w) for w in re.sub(r"\[.*?\]|\(.*?\)", " ", r).split() if nm(w)]
        if not heard:
            continue
        # Score every position just ahead of the last anchor instead of demanding an
        # exact run: whisper mishears single words ("Metropolitan" came back as
        # "political"), and an exact-match rule threw the whole anchor away over one
        # wrong word. Two words agreeing out of the first four is enough to place it.
        want = heard[:4]
        best, second = (0, None), 0
        for i in range(at, min(len(on), at + last_free)):
            sc = sum(1 for k, w in enumerate(want)
                     if i + k < len(on) and _same(on[i + k], w))
            if sc > best[0]:
                second, best = best[0], (sc, i)
            elif sc > second:
                second = sc
        hit = best[1] if best[0] >= 2 else None
        if hit is None and len(want) == 1 and len(want[0]) >= 4 and want[0] not in COMMON:
            # one word only, and a distinctive one. NEVER on "and", "the", "so":
            # 23 Sept an onset where Kevin says "and they would sit and meditate"
            # matched the "and" of "and everyone around me" and dragged that whole
            # sentence 11.9s early, off a tarmac he does not reach for another ten
            # seconds. A common word is not evidence of position.
            near = [i for i in range(at, min(len(on), at + 5)) if on[i] == want[0]]
            hit = near[0] if len(near) == 1 else None
        if hit is None:
            continue
        if abs(words[hit][0] - t) > MAX_PULL:
            continue            # no anchor moves a word further than a clock can drift
        pts.append((hit, t))
        at = hit + 1
    # NOT drop_impossible here. That guard compares the true span against OUR span
    # and throws out anchors that demand a big change of speed - which is exactly
    # what a compressed hesitation needs ("my"->"ultimate" is 0.17s in our clock
    # and 0.79s in the sound, a ratio of 4.6). It was silently deleting every
    # correction. Identity already proves the pairing; all that is left to catch is
    # an absurdity, so the test is on the SOUND alone: words per second between two
    # anchors must be something a person could say.
    ok = [pts[0]] if pts else []
    for i, t in pts[1:]:
        j, u = ok[-1] if ok else (None, None)
        rate = (i - j) / (t - u) if t > u else 99.0
        if 0.3 <= rate <= 9.0:
            ok.append((i, t))
    return ok


def warp_by_index(words, pts):
    """Stretch the times between anchors, keyed on the WORD, not on the clock.

    Warping by time alone cannot separate two words whisper gave the same
    timestamp ("to" and "my" both at 5.32s): the first anchor swallows both and
    the second is wasted. Between two anchored words the original times are used
    to space the words in between, and where those times are degenerate the words
    are spread evenly - a sentence read at a steady rate, which is closer to the
    truth than a pile at one instant.
    """
    if len(pts) < 2:
        return list(words)
    out = list(words)
    def put(i, t):
        e = max(out[i][1] + (t - out[i][0]), t + 0.06)
        out[i] = (round(t, 3), round(e, 3), out[i][2])
    for (i1, t1), (i2, t2) in zip(pts, pts[1:]):
        put(i1, t1)
        o1, o2 = words[i1][0], words[i2][0]
        for i in range(i1 + 1, i2):
            if o2 > o1:
                f = (words[i][0] - o1) / (o2 - o1)
            else:
                f = (i - i1) / (i2 - i1)
            put(i, t1 + f * (t2 - t1))
    put(pts[-1][0], pts[-1][1])
    d0 = pts[0][1] - words[pts[0][0]][0]
    for i in range(0, pts[0][0]):
        put(i, words[i][0] + d0)
    dn = pts[-1][1] - words[pts[-1][0]][0]
    for i in range(pts[-1][0] + 1, len(words)):
        put(i, words[i][0] + dn)
    for i in range(1, len(out)):                      # never let a word start before the one before it
        if out[i][0] < out[i - 1][0]:
            out[i] = (out[i - 1][0], max(out[i][1], out[i - 1][0] + 0.06), out[i][2])
    return out


if __name__ == "__main__":
    import glob
    import vsc_v2caps as V
    from vsc_cuts import CUTS
    ab = json.load(open(os.path.join(WORK, "v2_ab.json")))
    pre = {n: p for p, cl in CUTS.items() for n, *_ in cl}
    close = {n: c for p, cl in CUTS.items() for n, r, f, c, h in cl}
    fixes = json.load(open(os.path.join(WORK, "v2_fixes.json")))
    allerr = []
    for name in (sys.argv[1:] or sorted(ab)):
        r = ab[name]
        src = glob.glob(os.path.expanduser(f"~/Desktop/VSC/Source/{pre[name]}*.mp4"))[0]
        # always from the ORIGINAL transcription: corrections, then timing. Running
        # this twice must give the same answer as running it once.
        V.refinish(name, close[name], fixes.get(name, []))
        _n, errs = retime(name, src, r["a"], r["b"])
        allerr += errs
    if allerr:
        se = sorted(allerr, key=abs)
        late = [e for e in allerr if e > 0.25]
        print(f"ALL 29 before: {len(allerr)} anchors, median |error| {abs(se[len(se)//2]):.2f}s, "
              f"worst {max(allerr, key=abs):+.2f}s, {len(late)} captions late by more than 0.25s")
    print("V2TIMEDONE")

def anchor_words(src, a, b, words, quiet=False):
    """Pin one clip's words to the SOUND. [(start, end, text)] in, same shape out.

    The one call any renderer needs. Everything else in this module is the machinery
    behind it: find where speech resumes, read 1.4s from each of those moments, match
    the word HEARD there to the script, and stretch the times between the anchors.

    Why a renderer should use it: whisper reading a whole clip compresses filled pauses.
    On one clip the speaker hesitated - "to, uh, uh, my ultimate prison" - and the word
    "prison" was timed at 6.06s when he says it at 8.13s. Every other check passed that
    clip. Anchoring by nearest-in-time cannot fix it either, because a word two seconds
    adrift gets pinned to the wrong silence and the error is locked in. Only asking
    WHICH WORD IS HEARD at each pause recovers it.

    Costs one short transcription per pause, so roughly 20-60 seconds for a 60-second
    clip. Returns the words untouched if too few anchors are found to be trustworthy.
    """
    import tempfile
    if not words:
        return words
    wav = os.path.join(tempfile.gettempdir(), "anchor_%d.wav" % abs(hash((src, a, b))))
    subprocess.run([FF, "-y", "-loglevel", "error", "-ss", f"{a:.3f}", "-to", f"{b:.3f}",
                    "-i", src, "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", wav], check=True)
    try:
        ons = onsets(envelope(src, a, b))
        pts = anchor_by_identity(wav, [tuple(w) for w in words], ons)
        if len(pts) < 2:
            if not quiet:
                print(f"      caption timing: only {len(pts)} anchor(s), left as transcribed")
            return words
        out = warp_by_index([tuple(w) for w in words], pts)
        if not quiet:
            moved = max(abs(o[0] - n[0]) for o, n in zip(words, out))
            print(f"      caption timing: {len(pts)} anchors of {len(ons)} sounds, "
                  f"worst correction {moved:.2f}s")
        return out
    finally:
        if os.path.exists(wav):
            os.remove(wav)
