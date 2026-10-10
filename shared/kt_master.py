#!/usr/bin/env python3
"""ONE master transcript per episode; every clip's captions are CUT from it.

OPT-IN, DEFAULT OFF. Nothing changes unless MASTER_TRANSCRIPT=1 is set AND a master
file exists for the source. Without both, kt_words.words_for() and VSC's
accurate_words() run exactly as before (the CAPTION_SHIFT pattern, PRs 18/19).

WHY, 9 Oct 2026. Kamay: captions are the one block left - "simple, light, cheap,
PERFECT, I don't care how". The diagnosis:
  - every factory transcribes with whisper ggml-small.en, the weakest practical model;
  - captions are re-transcribed PER CLIP WINDOW, so each clip carries its own errors,
    and a caption `fix` must match that one clip's text letter for letter. Move an
    edge and the fixes silently stop matching ("CORRECTION NOT APPLIED"), or stack
    ("problems. problems.");
  - nothing checks MEANING (QC_AGENT.md, Layer 2): "Steven Jobs" passes every
    mechanical check.
So: transcribe the WHOLE episode once (free whisper.cpp on the runner), have ONE Claude
call correct it (word-level edits only, validated by code: no timing changes outside
an edit, bounded, nothing invented), and cut every clip's captions from that. A
correction is written once per episode and moving an edge never breaks it.

    python kt_master.py build <video> --engine whisper:<ggml model> [--correct]
    python kt_master.py build <video> --engine whisper+names:<ggml model>   # names as prompt
    python kt_master.py cut <video> <t0> <t1>          # what a clip would get

A master lives at $MASTER_DIR/<video stem>.master.json (default ~/Kamay/masters).
It holds Kevin's words: keep it on the runner, and store it only encrypted.
"""
import difflib
import json
import os
import re
import subprocess
import sys
import time

HOME = os.path.expanduser("~/Kamay")
MASTER_DIR = os.environ.get("MASTER_DIR") or os.path.join(HOME, "masters")
FFMPEG = os.path.join(HOME, "bin/ffmpeg") if os.path.exists(os.path.join(HOME, "bin/ffmpeg")) else "ffmpeg"
WHISPER = os.environ.get("WHISPER_CLI") or os.path.join(HOME, "whisper.cpp/build/bin/whisper-cli")
MODEL = os.environ.get("MASTER_MODEL") or "claude-opus-5-5"

# THE NAMES TO LISTEN FOR. QC_AGENT.md's list plus the whisper breaks CLAUDE.md
# records (vsc-factory). Engines that take key terms get them; the correction call
# always gets them. Add a name here the first time a caption gets one wrong.
NAMES = [
    "Kevin Trudeau", "Steve Jobs", "NeXT", "Apple", "Bobby Singer", "J.K. Rowling",
    "Harry Potter", "Viktor Frankl", "Natural Cures", "Your Wish Is Your Command",
    "Mega Memory", "FTC", "GIN", "Global Information Network",
    "New York Times bestseller list", "Carnegie Deli", "American Memory Institute",
    "Possibility Thinker's Creed", "Robert Schuller", "samskaras", "tummo",
    "counter-intention", "the Brotherhood", "Okinawa", "Ojai", "Lynn Shore Drive",
    "Swampscott", "Napoleon Hill", "Think and Grow Rich", "Infomercial",
]

MARKUP = re.compile(r"^[\[\(\*].*[\]\)\*][.,!?]?$")          # [BLANK_AUDIO] (laughing) *music*
FILLER = re.compile(r"^(um+|uh+|erm|ah|mm+|hmm+)[,.!?]?$", re.I)


def enabled():
    return os.environ.get("MASTER_TRANSCRIPT") == "1"


def norm(t):
    return re.sub(r"[^a-z0-9']", "", str(t).lower())


def letters(ws):
    return "".join(norm(w) for w in ws)


def path_for(src):
    if os.environ.get("MASTER_FILE"):
        return os.environ["MASTER_FILE"]
    stem = os.path.splitext(os.path.basename(src))[0]
    return os.path.join(MASTER_DIR, stem + ".master.json")


# --------------------------------------------------------------------------- engines
# Every engine returns [(start, end, word)] in ABSOLUTE seconds, punctuation attached
# to the word ("Jobs," "list."), because kt_render.phrases_from_words breaks on it.

def wav_of(src, wav):
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", src, "-vn", "-ar", "16000",
                    "-ac", "1", "-c:a", "pcm_s16le", wav], check=True)
    return wav


def whisper_cpp(wav, model, prompt=None):
    """whisper.cpp over the whole file, words rebuilt from its token timestamps.

    Normal (segment) mode, NOT `-ml 1`: a prompt in one-word mode compressed every
    timestamp by up to 9.5 s (kt_words.py, 14-16 Sept). In segment mode the prompt
    is what lets the model spell names; the benchmark measures whether its times
    hold up (stt_test in vsc-factory scores timing as well as words).
    """
    base = wav[:-4] + "_wcpp"
    cmd = [WHISPER, "-m", model, "-f", wav, "-ojf", "-of", base, "-t", str(os.cpu_count() or 4)]
    if prompt:
        cmd += ["--prompt", prompt]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if not os.path.exists(base + ".json"):
        raise RuntimeError(f"whisper produced nothing (exit {r.returncode}): {r.stderr[-400:]}")
    j = json.load(open(base + ".json", encoding="utf-8", errors="replace"))
    out = []
    for seg in j.get("transcription", []):
        for tok in seg.get("tokens", []):
            t = tok.get("text", "")
            if not t or t.startswith("[_") or t.startswith("<|"):
                continue
            off = tok.get("offsets")
            if off:
                a, b = off["from"] / 1000.0, off["to"] / 1000.0
            else:                                      # a token can lack its own times:
                a = out[-1][1] if out else seg["offsets"]["from"] / 1000.0   # it follows the last
                b = a
            if t.startswith(" ") or not out:
                if t.strip():
                    out.append([a, b, t.strip()])
            else:
                out[-1][1] = max(out[-1][1], b)
                out[-1][2] += t
    return [(round(a, 3), round(max(b, a + 0.02), 3), w) for a, b, w in out if w.strip()]


def transcribe(wav, engine, names=NAMES):
    """engine: whisper:<ggml model path>, or whisper+names:<path> (names as the prompt).

    FREE ONLY (Kamay, 9 Oct 2026): no paid speech-to-text, ever. The one paid piece is
    the Claude correction pass below, cents per episode on the existing key."""
    kind, model = engine.split(":", 1)
    prompt = ("Kevin Trudeau talks about " + ", ".join(names) + ".") if kind == "whisper+names" else None
    return whisper_cpp(wav, model, prompt)


def collapse_stutters(words):
    """'I'm I'm the genius' -> 'I'm the genius'. Only an EXACT repeat with no punctuation
    on the first copy: Kevin's emphasis is punctuated ("attacking, attacking"), damage is
    not (QC_AGENT.md) - and kt_qc fails an unpunctuated repeat anyway."""
    out = []
    for w in words:
        if out and w[2] == out[-1][2] and norm(w[2]) and not re.search(r"[.,!?;:]$", out[-1][2]):
            out[-1] = (out[-1][0], w[1], w[2])          # one word, spanning both
            continue
        out.append(tuple(w))
    return out


# ------------------------------------------------------------------------ correction
SCHEMA = {
    "type": "object",
    "properties": {
        "edits": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "line": {"type": "integer"},
                    "wrong": {"type": "string"},
                    "right": {"type": "string"},
                    "why": {"type": "string"},
                },
                "required": ["line", "wrong", "right", "why"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["edits"],
    "additionalProperties": False,
}

BRIEF = """You proofread a machine transcript of one episode. It will be burned into
short-form video captions word for word, and reviewers read every line.

Speaker: Kevin Trudeau (author of Natural Cures, Your Wish Is Your Command, Mega
Memory; founder of GIN, the Global Information Network), usually in an interview.

Names and terms he uses, spelled correctly:
{names}

Return ONLY corrections of words the machine got WRONG:
- misheard words and misspelled names ("Steven Jobs" -> "Steve Jobs", "next" -> "NeXT"
  where he means the company, "best settle list" -> "bestseller list");
- where Kevin misspeaks and the meaning is obvious, write what he meant;
- whisper markup or words nobody said ("[BLANK_AUDIO]", "(laughing)", a stray "Sorry."
  over silence): right = "".
- a word the machine doubled by accident ("the the" with no comma) -> one copy. Kevin's
  deliberate repetition ("tons and tons", "attacking, attacking") stays.

Never: rephrase, tidy grammar he really spoke, add words he did not say, change
punctuation or capitals for style, or touch a word you are not sure is wrong.
Fewer, certain edits beat many guesses.

A line may be followed by "~" notes: there a SECOND speech model heard something
different. Neither model is always right - it is a clue where to look, judged by
meaning. Never copy a "~" note into `wrong`; `wrong` is always words from an L line.

Each edit: `line` = the L-number where the wrong words START; `wrong` = the exact words
as they appear in the transcript (copy them, 1-6 words, may run onto the next line);
`right` = what he said; `why` = a few words."""


def hints(words, other, per=18):
    """{line: ['"this" / other model: "that"', ...]} where a second engine disagrees.

    9 Oct 2026, master-test: the correction pass missed "NeXT because he that I know"
    (he says "because he says, I know") - nothing in the text alone says it is wrong. A
    second free model hearing the same audio differently is exactly that signal."""
    a, b = [norm(w[2]) for w in words], [norm(w[2]) for w in other]
    out = {}
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if tag == "replace" and i2 - i1 <= 6 and j2 - j1 <= 6:
            here = " ".join(w[2] for w in words[i1:i2])
            alt = " ".join(w[2] for w in other[j1:j2])
            out.setdefault(i1 // per, []).append(f'"{here}" / other model: "{alt}"')
    return out


def lines_of(words, per=18, notes=None):
    out = []
    for k in range(0, len(words), per):
        t = words[k][0]
        out.append(f"L{k // per} [{int(t // 60)}:{int(t % 60):02d}] " + " ".join(w[2] for w in words[k:k + per]))
        for n in (notes or {}).get(k // per, []):
            out.append(f"   ~ {n}")
    return "\n".join(out)


def _find_run(words, toks, lo, hi):
    """Index where the exact run `toks` starts within [lo, hi), exact text first, then normalised."""
    for key in (lambda s: s, norm):
        want = [key(t) for t in toks]
        for i in range(max(0, lo), min(len(words), hi) - len(want) + 1):
            if [key(words[i + k][2]) for k in range(len(want))] == want:
                return i
    return None


def _allowed(wrong, right, vocab):
    """Code's veto: is this a correction, or an invention?"""
    if len(wrong) > 6 or len(right) > len(wrong) + 2:
        return "too long"
    if not right:
        if all(MARKUP.match(w) or FILLER.match(w) for w in wrong):
            return None
        if len(wrong) % 2 == 0 and [norm(w) for w in wrong[:len(wrong) // 2]] == [norm(w) for w in wrong[len(wrong) // 2:]]:
            return None
        return "deletes real words"
    a, b = letters(wrong), letters(right)
    if a == b:
        return None                                   # spacing/punctuation/capitals: harmless
    new = [norm(w) for w in right if norm(w) and norm(w) not in {norm(x) for x in wrong}]
    if all(t in vocab for t in new):
        return None                                   # brings in a known name/term
    if difflib.SequenceMatcher(a=a, b=b, autojunk=False).ratio() >= 0.5:
        return None                                   # sounds-alike correction
    # a doubled word collapsed: "the the" -> "the"
    if len(right) < len(wrong) and set(norm(w) for w in right) <= set(norm(w) for w in wrong):
        return None
    return "not a correction of these words"


def apply_edits(words, edits, per=18, names=NAMES, heard=()):
    """Apply validated word edits. Timing outside an edit never moves; an edit's new
    words share its span by length. Edits never overlap (no stacking, ever).
    `heard`: words a second engine heard where it disagreed - real audio, not invention."""
    vocab = {norm(t) for n in names for t in n.split()} | set(heard)
    words = [tuple(w) for w in words]
    cap = max(25, len(words) // 25)
    taken, rejected, plan = [], [], []
    used = set()
    for e in edits:
        wrong, right = e["wrong"].split(), e["right"].split()
        why = _allowed(wrong, right, vocab) if wrong else "empty"
        i = None
        if not why:
            i = _find_run(words, wrong, (e["line"] - 1) * per, (e["line"] + 2) * per)
            why = None if i is not None else "words not found on that line"
        if not why and any(k in used for k in range(i, i + len(wrong))):
            why = "overlaps another edit"
        if not why and len(plan) >= cap:
            why = f"over the cap of {cap} edits"
        if why:
            rejected.append(dict(e, rejected=why))
            continue
        used.update(range(i, i + len(wrong)))
        plan.append((i, len(wrong), right, e))
    for i, n, right, e in sorted(plan, key=lambda x: -x[0]):  # back to front: indices stay valid
        ts, te = words[i][0], words[i + n - 1][1]
        new, t = [], ts
        tot = sum(len(w) for w in right) or 1
        for w in right:
            d = (te - ts) * len(w) / tot
            new.append((round(t, 3), round(t + d, 3), w))
            t += d
        words[i:i + n] = new
        taken.append(dict(e, at=round(ts, 2)))
    return words, sorted(taken, key=lambda x: x["at"]), rejected


def correct(words, context="", names=NAMES, model=MODEL, other=None):
    """ONE Claude call (no tools, structured output) proposes edits; code decides.

    Returns (words, taken, rejected, usage). Without ANTHROPIC_API_KEY, or if the call
    fails, the words come back untouched - a correction pass never loses captions.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("  no ANTHROPIC_API_KEY - master left uncorrected", flush=True)
        return words, [], [], None
    import anthropic
    client = anthropic.Anthropic()
    system = BRIEF.format(names=", ".join(names)) + (f"\n\nThis episode: {context}" if context else "")
    try:
        with client.messages.stream(
                model=model, max_tokens=32000, system=system,
                messages=[{"role": "user", "content": "Transcript:\n\n" + lines_of(
                    words, notes=hints(words, other) if other else None)}],
                output_config={"effort": "high", "format": {"type": "json_schema", "schema": SCHEMA}},
        ) as s:
            r = s.get_final_message()
    except anthropic.APIError as e:
        print(f"  correction call failed ({e}) - master left uncorrected", flush=True)
        return words, [], [], None
    if r.stop_reason == "refusal":
        print("  correction declined by the model - master left uncorrected", flush=True)
        return words, [], [], None
    text = next((b.text for b in r.content if b.type == "text"), "")
    try:
        edits = json.loads(text)["edits"]
    except Exception:
        print("  correction answer unreadable - master left uncorrected", flush=True)
        return words, [], [], None
    heard = set()
    if other:
        a, b = [norm(x[2]) for x in words], [norm(x[2]) for x in other]
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
            if tag == "replace":
                heard.update(b[j1:j2])
    w, taken, rejected = apply_edits(words, edits, names=names, heard=heard)
    u = r.usage
    usage = {"input": u.input_tokens, "output": u.output_tokens,
             "usd": round(u.input_tokens * 4e-6 + u.output_tokens * 20e-6, 4)}
    return w, taken, rejected, usage


def apply_fixes(words, fixes):
    """Human corrections written ONCE per episode, against the master, in SOURCE seconds:
    [[t, "wrong words", "right words"], ...]. Applied in order, never over each other."""
    words = [tuple(w) for w in words]
    spans = []                                         # (start, end) already corrected
    for t, wrong, right in fixes:
        toks = [norm(x) for x in wrong.split()]
        best = None
        for i in range(len(words) - len(toks) + 1):
            if [norm(words[i + k][2]) for k in range(len(toks))] == toks:
                d = abs(words[i][0] - t)
                if d <= 12 and (best is None or d < best[0]):
                    best = (d, i)
        hit = best and (words[best[1]][0], words[best[1] + len(toks) - 1][1])
        if not hit or any(a < hit[1] and hit[0] < b for a, b in spans):
            print(f"  !! MASTER FIX NOT APPLIED: '{wrong}' near {t}s", flush=True)
            continue
        i = best[1]
        words, _, _ = apply_edits(words, [{"line": i // 18, "right": right, "why": "human",
                                           "wrong": " ".join(w[2] for w in words[i:i + len(toks)])}],
                                  names=[right])
        spans.append(hit)
    return words


# ----------------------------------------------------------------------------- use
_cache = {}


def load(src):
    p = path_for(src)
    if p not in _cache:
        _cache[p] = json.load(open(p)) if os.path.exists(p) else None
    return _cache[p]


def cut(src, t_in, t_out, timed=None):
    """Clip-relative [(start, end, word)] for t_in..t_out, or None when there is no master
    (the caller then does exactly what it did before).

    With `timed` (the window's own per-clip timing pass, clip-relative), the master
    gives the WORDS and `timed` gives the TIMES and the edges. 9 Oct 2026, master-test:
    whole-episode token times were looser than the per-window pass (turbo 260/780 ms
    median/p90 against 220/676) and cutting by time alone dropped "So flip" off the
    head of a KT clip. Aligning the two keeps the first and last words the window
    really hears, and every caption on the times that were graded against the sound."""
    m = load(src)
    if not m:
        print(f"  no master transcript at {path_for(src)} - per-clip transcription", flush=True)
        return None
    if not timed:
        return [(round(a - t_in, 3), round(b - t_in, 3), w) for a, b, w in m["words"]
                if t_in <= (a + b) / 2 < t_out]
    mw = [(a - t_in, b - t_in, w) for a, b, w in m["words"] if t_in - 4 <= a < t_out + 4]
    tw = [tuple(x) for x in timed if norm(x[2])]
    mn, tn = [norm(w[2]) for w in mw], [norm(w[2]) for w in tw]
    blocks = [b for b in difflib.SequenceMatcher(a=mn, b=tn, autojunk=False).get_matching_blocks() if b.size >= 2]
    if not blocks:
        print("  master and window do not line up - window words kept", flush=True)
        return list(timed)
    lo = max(0, blocks[0].a - blocks[0].b)
    hi = min(len(mw), blocks[-1].a + blocks[-1].size + (len(tw) - blocks[-1].b - blocks[-1].size))
    mw, mn = mw[lo:hi], mn[lo:hi]
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=mn, b=tn, autojunk=False).get_opcodes():
        if tag == "equal" or (tag == "replace" and i2 - i1 == j2 - j1):
            out += [(tw[j1 + k][0], tw[j1 + k][1], mw[i1 + k][2]) for k in range(i2 - i1)]
        elif tag in ("replace", "delete"):
            # master words the window heard differently (or not at all): they share the
            # window's span for them, or the gap they sit in, by length
            ts = tw[j1][0] if j2 > j1 else (tw[j1 - 1][1] if j1 else mw[i1][0])
            te = tw[j2 - 1][1] if j2 > j1 else (tw[j1][0] if j1 < len(tw) else mw[i2 - 1][1])
            te = max(te, ts + 0.08 * (i2 - i1))
            ws = [mw[k][2] for k in range(i1, i2)]
            tot, t = sum(len(w) for w in ws) or 1, ts
            for w in ws:
                d = (te - ts) * len(w) / tot
                out.append((t, t + d, w))
                t += d
        # "insert": a word only the window heard - the corrected master wins, it goes
    return [(round(a, 3), round(b, 3), w) for a, b, w in out]


def build(src, engine, correct_it=False, context="", fixes=(), out=None, second=None):
    """`second`: another free engine whose disagreements the correction pass is shown."""
    os.makedirs(MASTER_DIR, exist_ok=True)
    wav = wav_of(src, os.path.join("/tmp", f"master_{os.getpid()}.wav"))
    t0 = time.time()
    raw = collapse_stutters(transcribe(wav, engine))
    other = collapse_stutters(transcribe(wav, second)) if second and correct_it else None
    took = round(time.time() - t0, 1)
    words, taken, rejected, usage = (correct(raw, context, other=other) if correct_it else (raw, [], [], None))
    words = apply_fixes(words, fixes) if fixes else words
    m = {"src": os.path.basename(src), "engine": engine + (f" (+{second} hints)" if other else ""), "seconds": took, "words": words,
         "raw": raw, "edits": taken, "rejected": rejected, "usage": usage}
    p = out or path_for(src)
    json.dump(m, open(p, "w"), indent=0)
    print(f"  master: {len(words)} words, {engine}, {took}s, {len(taken)} edits taken, "
          f"{len(rejected)} refused -> {p}", flush=True)
    return m


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["build"]:
        eng = a[a.index("--engine") + 1]
        ctx = a[a.index("--context") + 1] if "--context" in a else ""
        build(a[1], eng, "--correct" in a, ctx)
    elif a[:1] == ["cut"]:
        for w in cut(a[1], float(a[2]), float(a[3])) or []:
            print(f"{w[0]:8.2f} {w[1]:8.2f} {w[2]}")
    else:
        print(__doc__)
