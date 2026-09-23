"""Check a clip plan before it is pushed (weekly agent). Exit 1 on any problem.

    python factory/check_plan.py factory/plans/ep_<id>.json [...]
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "pipeline"))
def _core(h, b):
    """The fallback. It enforces ONLY the hard rule - six words - and nothing
    else. 23 Sept 2026: a stricter fallback ("must open Why/How/What") threw out
    two whole episodes of good plans, including "He lost $65 million. Then this."
    A stand-in for a check must never be harsher than the check itself."""
    errs = []
    n = sum(len(l.split()) for l in h if l.strip())
    if not h or n == 0: errs.append("no hook")
    if n > 6: errs.append(f"{n} words - max 6")
    return errs


# THE REAL LINT IF IT LOADS, THE CORE RULES IF IT DOES NOT - NEVER A CRASH.
# 23 Sept 2026: two good plans were REJECTED by the merge job because kt_hooks
# pulls in the renderer, the renderer wants a font file, and that runner has no
# ~/Kamay. A missing font must never be able to throw away an episode's work.
try:
    import kt_hooks
    _real = kt_hooks.problems
    _real(["How rich people", "actually buy houses"], "KT_TEST")     # prove it runs
except Exception as e:
    print(f"(hook lint unavailable: {type(e).__name__}: {str(e)[:80]}; using the core rules)")
    _real = None


def lint(h, b):
    if _real is None:
        return _core(h, b)
    try:
        return _real(h, b)
    except Exception as e:
        print(f"(hook lint failed on {h}: {type(e).__name__}; using the core rules)")
        return _core(h, b)

# WORD OVEREXPOSURE. A hook word that appears in more than a third of recent
# posts has stopped differentiating anything - it sits in the winners and the
# losers alike, so it can no longer be why either happened. Retire it for a
# season. (Daniel's system, Sept 2026, and it is the one rule here measured
# against what actually went out rather than against taste.)
STOP = set("a an and the is are was were be to of in on for it its this that with you your my his "
           "her their our how why what when who not no do does did can will would should i he she they "
           "we me him them from at as by or if so but into about more most just only".split())


def overexposed(recent, limit=1 / 3):
    from collections import Counter
    n = len(recent)
    if n < 12:
        return {}
    c = Counter()
    for h in recent:
        c.update({w for w in re.findall(r"[a-z']+", h.lower()) if w not in STOP and len(w) > 2})
    return {w: k for w, k in c.items() if k / n > limit}


def recent_hooks(n=40):
    try:
        man = json.load(open(os.path.join(os.path.dirname(HERE), "state", "manifest.json")))["clips"]
    except Exception:
        return []
    posted = [c for c in man if c.get("posted_at") and c.get("hook") and not c["file"].startswith("AR_")]
    return [c["hook"] for c in sorted(posted, key=lambda c: c["posted_at"])[-n:]]


bad = 0
tired = overexposed(recent_hooks())
if tired:
    print("worn-out hook words (in over a third of recent posts): "
          + ", ".join(f"{w} x{k}" for w, k in sorted(tired.items(), key=lambda x: -x[1])))
others = {}
for f in os.listdir(os.path.join(HERE, "plans")):
    if f.endswith(".json") and not f.startswith("_"):
        try: others[f] = json.load(open(os.path.join(HERE, "plans", f)))
        except Exception: pass
for path in sys.argv[1:]:
    p = json.load(open(path)); name = os.path.basename(path); errs = []
    b = p.get("brand", "")
    if not re.fullmatch(r"KT_[A-Z0-9]+", b): errs.append(f"brand '{b}' must be KT_<ONEWORD>")
    if any(o.get("brand") == b for f, o in others.items() if f != name): errs.append(f"brand {b} already used by another plan")
    if not re.fullmatch(r"v[a-z0-9]+\.mp4", p.get("source", "")): errs.append("source must be <rumble id>.mp4")
    slugs = [c.get("slug") for c in p.get("clips", [])]
    if len(slugs) != len(set(slugs)): errs.append("duplicate slugs")
    for c in p.get("clips", []):
        s = c.get("slug", "?"); d = float(c["out"]) - float(c["in"])
        if not re.fullmatch(r"[A-Z0-9]+(-[A-Z0-9]+)*", s): errs.append(f"{s}: slug must be UPPER-DASHED")
        if not 40 <= d <= 190: errs.append(f"{s}: length {d:.0f}s outside 40-190")
        for e in lint(c.get("hook") or [], b): errs.append(f"{s}: hook - {e}")
        worn = [w for w in re.findall(r"[a-z']+", " ".join(c.get("hook") or []).lower()) if w in tired]
        if worn: errs.append(f"{s}: hook leans on worn-out word(s): {', '.join(sorted(set(worn)))}")
        cap = c.get("caption", "")
        if not 300 <= len(cap) <= 750: errs.append(f"{s}: caption {len(cap)} chars (want 400-600)")
        if "#kevintrudeau" not in cap: errs.append(f"{s}: caption needs #kevintrudeau")
        if c.get("cta_kind") not in (None, "offer"): errs.append(f"{s}: cta_kind must be 'offer' or absent")
        for k in ("start_words", "end_words"):
            n = len(str(c.get(k) or "").split())
            if not 2 <= n <= 8: errs.append(f"{s}: {k} must be the clip's exact first/last 3-5 words")
    print(f"{name}: {'OK' if not errs else 'PROBLEMS'} ({len(slugs)} clips)")
    for e in errs: print("   -", e)
    bad += bool(errs)
sys.exit(1 if bad else 0)
