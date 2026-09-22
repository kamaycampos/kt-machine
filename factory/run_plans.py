"""Turn committed clip plans into verified, queued clips - in the cloud.

A plan is factory/plans/<key>.json, the same shape kt_batch_build.py reads on the
Mac: {"source": "<youtube id>.mp4", "brand": "KT_...", "clips": [...]}. Plans are
written by a Claude session from the episode's transcript; everything after that
is mechanical and runs here with the Mac shut.

Every clip passes every gate the Mac uses (hook lint, ending verdict, render,
caption sync against the waveform, first/last seconds) plus one more: the source
must really be 1080p (18 Sept 2026 - 18 clips went out blurry from 360p copies).

A plan with "test": true is rendered and checked but NEVER uploaded or queued;
the clips come back as a workflow artifact for inspection.
"""
import json, os, re, shutil, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.expanduser("~/Kamay"))
from transcribe import fetch_source, sh  # noqa: E402

K = os.path.expanduser("~/Kamay")
HERE = os.path.dirname(os.path.abspath(__file__))
PLANS = os.path.join(HERE, "plans")
DONE = os.path.join(PLANS, "_done.json")
PROP = os.path.join(K, "work", "proposals")
OUT = "/tmp/factory_out"


def height(path):
    m = re.search(r"Video:.*?(\d{3,4})x(\d{3,4})", sh("ffmpeg", "-i", path).stderr)
    return int(m[2]) if m else 0


def _find_words(src, phrase, near, last):
    """Time of the planner's named words at word level: the END of the last word
    (last=True) or the START of the first. Tries the whole phrase, then its last
    (or first) 3 and 2 words - the two whisper passes spell some words
    differently. Only a match within 9s of the planned time counts; nearest wins."""
    if not phrase:
        return None
    import kt_words
    norm = lambda w: re.sub(r"[^a-z0-9']", "", w.lower())
    toks = [norm(w) for w in phrase.split() if norm(w)]
    G = 60.0
    t0 = max(0.0, (int(near // G) - 1) * G)
    t1 = (int(near // G) + 2) * G
    ws = [(t0 + rs, t0 + re_, norm(w)) for rs, re_, w in
          kt_words.words_for(src, t0, t1, f"PAYOFF/{os.path.basename(src)}") if norm(w or "")]
    for n in sorted({len(toks), min(3, len(toks)), min(2, len(toks))}, reverse=True):
        want = toks[-n:] if last else toks[:n]
        hits = [(ws[i + n - 1][1] if last else ws[i][0]) for i in range(len(ws) - n + 1)
                if [w for _, _, w in ws[i:i + n]] == want]
        hits = [h for h in hits if abs(h - near) <= 9.0]
        if hits:
            return min(hits, key=lambda h: abs(h - near))
    return None


def fix_edges(key):
    """Put each cut on a real sentence boundary, measured at WORD level here.

    19 Sept 2026: plans are written from a transcript whose cue times are rounded
    to whole seconds, and 6 of the first 8 cloud clips failed the ending check by
    a fraction of a second. So the cut is settled here, where the words are: the
    start moves to the true start of its sentence; a failing end moves to the
    nearest sentence end that passes kt_payoff.verdict - LATER first (Kamay's
    rule: always run on to the payoff), then earlier. Every move is printed.
    """
    import kt_payoff
    path = os.path.join(PLANS, f"{key}.json")
    p = json.load(open(path))
    src = os.path.join(K, "Kamay Content", "1_RAW", "KT_SOURCE", p["source"])
    keep = []
    for c in p["clips"]:
        a, b = float(c["in"]), float(c["out"])
        # 22 Sept 2026: the planner now NAMES the clip's first and last words
        # (start_words / end_words). Meaning is its job; landing on those exact
        # words is ours. "Run on to the next full stop" had carried a clean
        # ending 8s into the interviewer's next question, because the word pass
        # missed the full stop the planner could plainly read.
        sa = _find_words(src, c.get("start_words"), a, last=False)
        sb = _find_words(src, c.get("end_words"), b, last=True)
        if sa is not None or sb is not None:
            a = round(max(0.0, sa - 0.10), 2) if sa is not None else a
            b = round(sb + 0.15, 2) if sb is not None else b
            bar = kt_payoff.verdict(src, a, b)
            if bar.startswith("runs into"):
                print(f"  {c['slug']}: {bar} - dropped"); continue
            print(f"  {c['slug']}: named words {c['in']}-{c['out']} -> {a}-{b}"
                  f"{'' if sa is not None else ' (start words not found)'}{'' if sb is not None else ' (end words not found)'}")
            if sb is not None:
                if sa is None:
                    near = [s for s in kt_payoff.sentences(src, max(0, a - 20), a + 20) if abs(s[0] - a) <= 3.0]
                    if near:
                        a = round(max(0.0, min(near, key=lambda s: abs(s[0] - a))[0] - 0.10), 2)
                c["in"], c["out"] = a, b
                keep.append(c)
                continue
        near = [s for s in kt_payoff.sentences(src, max(0, a - 20), a + 20) if abs(s[0] - a) <= 3.0]
        if near:
            s0 = min(near, key=lambda s: abs(s[0] - a))
            a = round(max(0.0, s0[0] - 0.10), 2)
        if kt_payoff.verdict(src, a, b):
            ends = sorted({round(s[1], 2) for s in kt_payoff.sentences(src, max(0, b - 25), b + 25)})
            later = [e for e in ends if b < e <= b + 20]
            earlier = [e for e in reversed(ends) if b - 15 <= e <= b]
            fixed = next((e + 0.15 for e in later + earlier
                          if not kt_payoff.verdict(src, a, e + 0.15)), None)
            if fixed is None:
                print(f"  {c['slug']}: no passing ending within -15/+20s of {b} - dropped")
                continue
            print(f"  {c['slug']}: ending {b} -> {fixed:.2f}")
            b = round(fixed, 2)
        if (a, b) != (float(c["in"]), float(c["out"])):
            print(f"  {c['slug']}: cut {c['in']}-{c['out']} -> {a}-{b}")
        c["in"], c["out"] = a, b
        keep.append(c)
    p["clips"] = keep
    json.dump(p, open(path, "w"), indent=1, ensure_ascii=False)


def batch(keys, test):
    for f in os.listdir(PROP):
        if f.endswith(".json") and not f.startswith("_"):
            os.remove(os.path.join(PROP, f))
    for k in keys:
        shutil.copy(os.path.join(PLANS, f"{k}.json"), os.path.join(PROP, f"{k}.json"))
    env = dict(os.environ, **({"KT_FACTORY_NOQUEUE": "1"} if test else {}))
    r = subprocess.run([sys.executable, "-u", os.path.join(K, "kt_batch_build.py")],
                       cwd=K, env=env, text=True, capture_output=True)
    print(r.stdout[-6000:], r.stderr[-2000:])
    merged = json.load(open(os.path.join(PROP, "_merged.json"))) if os.path.exists(
        os.path.join(PROP, "_merged.json")) else []
    return [k for k in keys if k in merged]


def main():
    done = json.load(open(DONE)) if os.path.exists(DONE) else []
    plans = sorted(f[:-5] for f in os.listdir(PLANS) if f.endswith(".json") and not f.startswith("_"))
    todo = [k for k in plans if k not in done]
    print(f"{len(todo)} plan(s) to build: {todo}")
    ready = {True: [], False: []}
    for k in todo:
        p = json.load(open(os.path.join(PLANS, f"{k}.json")))
        vid = p["source"][:-4]
        mp4 = fetch_source(vid)
        h = height(mp4)
        if h < 1080:
            print(f"  {k}: REFUSED - source is {h}p, the gate is 1080p")
            continue
        fix_edges(k)
        ready[bool(p.get("test"))].append(k)
    built = []
    if ready[True]:
        built += batch(ready[True], test=True)
        os.makedirs(OUT, exist_ok=True)
        for root, _d, files in os.walk(os.path.join(K, "POST_TODAY")):
            for f in files:
                if f.endswith(".mp4") or f.endswith("__caps.json"):
                    shutil.copy(os.path.join(root, f), OUT)
    if ready[False]:
        built += batch(ready[False], test=False)
    json.dump(sorted(set(done + built)), open(DONE, "w"), indent=1)
    shutil.copy(os.path.join(K, "kt_series.json"), os.path.join(HERE, "kt_series.json"))
    rep = os.path.join(K, "work", "proposals", "BATCH_REPORT.md")
    if os.path.exists(rep):
        os.makedirs(os.path.join(HERE, "reports"), exist_ok=True)
        shutil.copy(rep, os.path.join(HERE, "reports", "latest.md"))
    print(f"built: {built}")


if __name__ == "__main__":
    main()
