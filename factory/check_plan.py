"""Check a clip plan before it is pushed (weekly agent). Exit 1 on any problem.

    python factory/check_plan.py factory/plans/ep_<id>.json [...]
"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lengths import MIN_LEN, MAX_LEN  # noqa: E402

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

# NO STAKES, NO HOOK. 5 Oct 2026, Kamay sent "WHY IT TOOK HER / 3 HOURS" (Ep. 86,
# KAMAY's account): "its so stupid, so useless... if i read that hook i absolutely pass
# by because it doesnt give me anything." It passed every rule above: opens on Why,
# carries a number, six words. A number is only a promise when it is attached to
# something the viewer wants, fears or recognises - "3 hours" of a stranger's walk is
# trivia. Same failure as "What a stranger / told him" and "The dog on / the nail".
# The hook must hold at least one of: the viewer (you/your), money or status, a loss
# or a cost, a result, or a named person/brand. KT brands only - Yaren's stab rule is
# her own. Against the 152 KT hooks planned to 5 Oct this flags 40, and they are
# the weak ones ("Why it took her 3 hours", "The camping trip that changed everything").
STAKES = re.compile(
    r"(\byou\b|\byour\b|\byou'?re\b|[$%]|\bmillion|\bbillion|\bthousand|"
    r"\brich|\bwealth|\bmoney|\bbroke|\bpoor|\bcash|\bincome|\bdebt|\bsales|\bprofit|"
    r"\bfortune|\bpaid|\bpay|\bfinanc|\bfreedom|\bmansion|\binvest|\bbusiness|\bpower|"
    r"\bsuccess|\bmillionaire|\bbillionaire|\bwin\b|\bwon\b|\bwinners?\b|\bfail|\blost\b|"
    r"\blos(e|es|ing)\b|\bcancer|\bheal|\bprison|\bdied|\bdeath|\bfired|\bbanned|\bsued|\bhabit|"
    r"\bfear|\bpain|\bsuffer|\bsecret|\blie\b|\bmistake|\bnever|\bstop|\bwork(s|ing)?\b|"
    r"\bmanifest)", re.I)


def no_stakes(h, b):
    if str(b).upper().startswith("AR"):
        return None
    t = " ".join(h)
    named = any(re.search(r"(?<!^)\b[A-Z][a-z]{2,}", l.strip()) for l in h)
    if STAKES.search(t) or named:
        return None
    return ("no stakes - names nothing the viewer gets, fears or recognises. A number "
            "alone is trivia (\"Why it took her / 3 hours\"). Hook the money, the cost, "
            "the result, or say it to YOU")


# The merge job DELETES a plan that fails. A wording judgement must never throw an
# episode away there, so it only warns there (HOOK_STAKES=warn); the planner, which
# can rewrite, gets it as an error.
STAKES_WARN = os.environ.get("HOOK_STAKES") == "warn"


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
    # THE FENCE, AT THE DOOR. An ar_*.json plan may only carry AR_ folders and an
    # ep_*.json plan only KT_ ones, and no source video may serve both accounts.
    fam = "AR" if name.startswith("ar_") else "KT"
    if not re.fullmatch(fam + r"_[A-Z0-9]+", b):
        errs.append(f"brand '{b}' must be {fam}_<ONEWORD> in {name}")
    for f, o in others.items():
        if o.get("source") == p.get("source") and f.startswith("ar_") != name.startswith("ar_"):
            errs.append(f"FENCE: {p.get('source')} is already cut for the other account in {f}")
    if any(o.get("brand") == b for f, o in others.items() if f != name): errs.append(f"brand {b} already used by another plan")
    if not re.fullmatch(r"v[a-z0-9]+\.mp4", p.get("source", "")): errs.append("source must be <rumble id>.mp4")
    slugs = [c.get("slug") for c in p.get("clips", [])]
    if len(slugs) != len(set(slugs)): errs.append("duplicate slugs")
    for c in p.get("clips", []):
        s = c.get("slug", "?"); d = float(c["out"]) - float(c["in"])
        if not re.fullmatch(r"[A-Z0-9]+(-[A-Z0-9]+)*", s): errs.append(f"{s}: slug must be UPPER-DASHED")
        if not MIN_LEN <= d <= MAX_LEN: errs.append(f"{s}: length {d:.0f}s outside {MIN_LEN:.0f}-{MAX_LEN:.0f}")
        for e in lint(c.get("hook") or [], b): errs.append(f"{s}: hook - {e}")
        ns = no_stakes(c.get("hook") or [], b)
        if ns and STAKES_WARN: print(f"   ~ {s}: hook - {ns}")
        elif ns: errs.append(f"{s}: hook - {ns}")
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
