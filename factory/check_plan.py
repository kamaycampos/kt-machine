"""Check a clip plan before it is pushed (weekly agent). Exit 1 on any problem.

    python factory/check_plan.py factory/plans/ep_<id>.json [...]
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "pipeline"))
try:
    import kt_hooks
    lint = lambda h, b: kt_hooks.problems(h, b)
except Exception as e:                                   # fall back to the core rules
    print(f"(hook lint module unavailable: {e}; using the core rules)")
    def lint(h, b):
        errs = []
        n = sum(len(l.split()) for l in h)
        if n > 6: errs.append(f"{n} words - max 6")
        if not re.match(r"(why|how|what)\b", (h[0] if h else "").lower()): errs.append("not a direct Why/How/What promise")
        return errs

bad = 0
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
        cap = c.get("caption", "")
        if not 300 <= len(cap) <= 750: errs.append(f"{s}: caption {len(cap)} chars (want 400-600)")
        if "#kevintrudeau" not in cap: errs.append(f"{s}: caption needs #kevintrudeau")
        if c.get("cta_kind") not in (None, "offer"): errs.append(f"{s}: cta_kind must be 'offer' or absent")
    print(f"{name}: {'OK' if not errs else 'PROBLEMS'} ({len(slugs)} clips)")
    for e in errs: print("   -", e)
    bad += bool(errs)
sys.exit(1 if bad else 0)
