"""Collect every shard's passing clips and queue them ONCE (cloud).

Shards render in parallel (build_shard.py); this is the single place that
touches the posting queue: merge each plan into kt_series.json (captions live
there), put the clips where add_clips.py expects them, upload + queue, carry
the call-to-action kind onto the manifest, record the plan as built, commit.
Test plans are reported and marked built but never queued.

    python factory/queue.py /tmp/shards
"""
import glob, json, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MACHINE = os.path.dirname(HERE)
K = os.path.expanduser("~/Kamay")
SERIES = os.path.join(K, "kt_series.json")
root = sys.argv[1]

results = [json.load(open(f)) for f in glob.glob(os.path.join(root, "*", "result.json"))]
by_plan = {}
for r in results:
    if not r.get("variant_shard"):                 # trial variants only (shard.py), no clips
        by_plan.setdefault(r["plan"], []).append(r)
sys.path.insert(0, K)
import kt_lock  # noqa: E402  (mark published clips before anything re-renders)
print("locked now published:", kt_lock.sync())
series = json.load(open(SERIES))
done = json.load(open(os.path.join(HERE, "plans", "_done.json")))
brands, kinds, report, looks = set(), {}, [], {}
# SECOND CHANCES. 6 Oct 2026: 205 clips planned, 103 queued - and every clip that
# failed a gate was simply gone, because a plan that yields one clip is "built".
# Both accounts ran dry. A failed clip is now written here with why it failed,
# routine_prep.py hands it back to the planner, and the planner re-cuts it.
FAILED = os.path.join(HERE, "plans", "_failed.json")
failed = json.load(open(FAILED)) if os.path.exists(FAILED) else {"clips": {}, "attempts": {}}
try:
    _queued_files = [c["file"] for c in json.load(open(os.path.join(MACHINE, "state", "manifest.json")))["clips"]]
except (OSError, ValueError, KeyError):
    _queued_files = []
RETIRE_AFTER = 2       # a plan that yields NOTHING this many runs is not retried as-is


def note_failures(plan, p, kept, text):
    """Every planned clip that did not reach the queue, with the gate's words."""
    # A CLIP AN EARLIER RUN ALREADY QUEUED IS NOT A FAILURE (20 Oct 2026): a re-build of a
    # finished plan cannot re-render it, and filing it here offered a POSTED clip back.
    queued = {c["slug"] for c in series.get(plan, {}).get("clips", [])
              if any(m.startswith(p["brand"] + "/") and f"_{c['slug']}_" in m for m in _queued_files)}
    for c in p["clips"]:
        if c["slug"] in kept or c["slug"] in queued:
            failed["clips"].pop(f"{plan}/{c['slug']}", None)
            continue
        why = [l.strip(" -*") for l in text.splitlines() if c["slug"] in l
               and any(k in l for k in ("FAIL", "drop", "NOT QUEUED", "refused"))]
        # a re-cut carries "retry_of": its tries continue the original's count, so
        # one clip is offered back at most MAX_TRIES times in all (routine_prep.py)
        prev = failed["clips"].get(c.get("retry_of", ""), {}).get("tries", 0)
        failed["clips"][f"{plan}/{c['slug']}"] = {
            "plan": plan, "source": p["source"], "brand": p["brand"],
            "tries": max(prev, failed["clips"].get(f"{plan}/{c['slug']}", {}).get("tries", 0)) + 1,
            "why": [w[:300] for w in why[:3]] or ["no clip came out of the render"],
            **{k: c[k] for k in ("slug", "in", "out", "start_words", "end_words", "hook") if k in c}}
for plan, rs in sorted(by_plan.items()):
    p = json.load(open(os.path.join(HERE, "plans", f"{plan}.json")))
    passed = [c for r in sorted(rs, key=lambda r: r["shard"]) for c in r["clips"]]
    report.append(f"## {plan}: {len(passed)} of {len(p['clips'])} clip(s) passed every gate"
                  + (" (TEST - not queued)" if p.get("test") else ""))
    for r in rs:
        rep = os.path.join(root, f"shard-{plan}-{r['shard']}", "report.md")
        if os.path.exists(rep):
            report.append(open(rep).read()[-3000:])
    # ONLY a plan that actually produced a clip (or a test) counts as built.
    # 19 Sept: an infrastructure failure marked all 8 clips done and they were
    # silently lost. A plan that yields nothing stays pending and is retried.
    if passed or p.get("test"):
        done.append(plan)
    if not passed and not p.get("test"):
        # 2 Oct - 6 Oct: ep_v733zpw failed the same four clips the same way on six
        # runs in a row. A render is deterministic; a retry of the same cut is the
        # same answer. After RETIRE_AFTER runs its clips go back to the planner.
        n = failed["attempts"][plan] = failed["attempts"].get(plan, 0) + 1
        if n >= RETIRE_AFTER:
            done.append(plan)
            note_failures(plan, p, set(), "\n".join(report))
            report.append(f"- **RETIRED** after {n} runs with nothing passing; its clips go back "
                          f"to the planner (factory/plans/_failed.json)")
    # A TEST MEETS THE LAST GATE TOO (4 Nov 2026). Look E's two cloud tests "passed every gate" and
    # its first real day queued nothing: a test plan skipped kt_qc, the one gate that refused it
    # ("awesome He"). A test is still never queued - it is only told what the queue would say.
    if p.get("test") and passed:
        import kt_qc
        for r in rs:
            d = os.path.join(root, f"shard-{plan}-{r['shard']}")
            for f in r["files"]:
                if f.endswith(".mp4") and "__" not in f:
                    v, why = kt_qc.check(os.path.join(d, f))
                    line = f"TEST last gate (kt_qc) {v.upper()} {f}" + (f": {'; '.join(why[:4])}" if why else "")
                    report.append(f"- {line}")
                    print(f"  {line}", flush=True)
    if p.get("test") or not passed:
        continue
    spec = series.setdefault(plan, {"source": p["source"], "brand": p["brand"],
                                    "note": p.get("note", ""), "clips": []})
    have = {c["slug"] for c in spec["clips"]}
    spec["clips"] += [{k: c[k] for k in ("slug", "in", "out", "hook", "caption", "cta_kind") if k in c}
                      for c in passed if c["slug"] not in have]
    bdir = os.path.join(K, "POST_TODAY", p["brand"])
    os.makedirs(bdir, exist_ok=True)
    # THE LAST GATE BEFORE A LIVE ACCOUNT. Kamay, 29 Sept: "make sure every single clip
    # is absolutely PERFECT... so their system doesn't post BS in our accounts."
    # Everything upstream checks its own work; this checks the FINISHED file one more
    # time, right at the boundary, and a clip it cannot vouch for is never copied into
    # the posting folder - so the poster cannot reach it even by accident.
    import kt_qc
    blocked = set()
    for r in rs:
        d = os.path.join(root, f"shard-{plan}-{r['shard']}")
        for f in r["files"]:
            if not (f.endswith(".mp4") and "__" not in f):
                continue
            v, why = kt_qc.check(os.path.join(d, f))
            if v == "fail" and kt_qc.trim_tail(os.path.join(d, f), why):
                print(f"  TRIMMED {f}: {why[0]} - now ends on the last full sentence", flush=True)
                v, why = kt_qc.check(os.path.join(d, f))
            if v == "fail":
                blocked.add(f)
                report.append(f"- **NOT QUEUED** `{f}` - {'; '.join(why[:3])}")
                print(f"  BLOCKED {f}: {'; '.join(why[:2])}", flush=True)
    if blocked:
        keep = {c["slug"] for c in passed
                if not any(f"_{c['slug']}_" in b for b in blocked)}
        passed = [c for c in passed if c["slug"] in keep]
        spec["clips"] = [c for c in spec["clips"] if c["slug"] in keep or c["slug"] in have]
    note_failures(plan, p, {c["slug"] for c in passed}, "\n".join(report))
    for r in rs:
        for f in r["files"]:
            if any(f.startswith(b[:-4]) for b in blocked):
                continue                       # the clip and its sidecar both stay behind
            shutil.copy(os.path.join(root, f"shard-{plan}-{r['shard']}", f), bdir)
            if f.endswith(".mp4") and "__" not in f and r.get("look"):
                looks[f"{p['brand']}/{f}"] = r["look"]          # the look test (build_shard.py)
            if f.endswith(".mp4") and "__" not in f and "cta_kind" in str(passed):
                slug = next((c for c in passed if f"_{c['slug']}_" in f), {})
                if slug.get("cta_kind"):
                    kinds[f"{p['brand']}/{f}"] = slug["cta_kind"]
    brands.add(p["brand"])
json.dump(series, open(SERIES, "w"), indent=1, ensure_ascii=False)
shutil.copy(SERIES, os.path.join(HERE, "kt_series.json"))
json.dump(sorted(set(done)), open(os.path.join(HERE, "plans", "_done.json"), "w"), indent=1)
json.dump(failed, open(FAILED, "w"), indent=1, ensure_ascii=False)
if brands:
    # NO PULL HERE (14 Oct 2026). kt_series.json, _done.json and _failed.json are already
    # written, so a plain pull refuses the dirty tree and an --autostash pull merged
    # them with conflict markers that the Save step then committed - every factory
    # run failed on kt_series.json until it was repaired. The queue job checks out
    # main itself (factory.yml), so the tree is current when this starts.
    up = subprocess.run([sys.executable, "add_clips.py", *sorted(brands)], cwd=MACHINE,
                        capture_output=True, text=True)
    report.append("## UPLOAD\n" + up.stdout[-2500:] + up.stderr[-500:])
    man_p = os.path.join(MACHINE, "state", "manifest.json")
    man = json.load(open(man_p))
    for c in man["clips"]:
        if kinds.get(c["file"]) and not c.get("posted_at") and not c.get("cta_kind"):
            c["cta_kind"] = kinds[c["file"]]
        if looks.get(c["file"]) and not c.get("look"):
            c["look"] = looks[c["file"]]
    json.dump(man, open(man_p, "w"), indent=1)
    subprocess.run([sys.executable, "make_thumbs.py"], cwd=MACHINE, capture_output=True)
# TRIAL REEL VARIANTS (1 Nov 2026, build_shard.py): upload each to the media release and list
# the experiment in state/variants.json; run_once.py posts them once the clip has posted.
_vp = os.path.join(MACHINE, "state", "variants.json")
try:
    _var = json.load(open(_vp))
except (OSError, ValueError):
    _var = {}
_man = [c["file"] for c in json.load(open(os.path.join(MACHINE, "state", "manifest.json")))["clips"]]
# variants roll over with the clips (media_store.py, 7 Nov 2026: `media` hit 1000 files)
sys.path.insert(0, MACHINE)
import media_store                                                 # noqa: E402
_store = media_store.Store("gh", os.environ.get("GITHUB_REPOSITORY", "kamaycampos/kt-machine"))
for r in sorted(results, key=lambda r: str(r["shard"])):
    for slug, vs in (r.get("variants") or {}).items():
        clip = next((f for f in _man if f.startswith(r["brand"] + "/") and f"_{slug}_" in f), None)
        old = _var.get(f"{r['brand']}__{slug}")
        if not clip or (old and old.get("posted")):
            continue
        # several variant shards add arms to ONE experiment (2 Nov 2026)
        arms = [a for a in (old or {}).get("arms", [])]
        have = {a["rel"] for a in arms}
        vs = [v for v in vs if "_VARIANTS/" + v["file"] not in have]
        for v in vs:
            src = os.path.join(root, f"shard-{r['plan']}-{r['shard']}", v["file"])
            asset = "_VARIANTS--" + v["file"]
            tmp = os.path.join("/tmp", asset)
            shutil.copy(src, tmp)
            try:
                _tag = _store.room(1)
            except RuntimeError as x:
                report.append(f"   VARIANT UPLOAD FAILED {v['file']}: {x}")
                continue
            up = subprocess.run(["gh", "release", "upload", _tag, tmp, "--clobber",
                                 "-R", os.environ.get("GITHUB_REPOSITORY", "kamaycampos/kt-machine")],
                                capture_output=True, text=True)
            if up.returncode == 0:
                _store.used()
                arms.append({"rel": "_VARIANTS/" + v["file"], "hook": v["hook"], "media_tag": _tag})
            else:
                report.append(f"   VARIANT UPLOAD FAILED {v['file']}: {up.stderr[-160:]}")
        if arms and vs:
            arms.sort(key=lambda a: a["rel"])
            _var[f"{r['brand']}__{slug}"] = {"clip": clip, "arms": arms, "posted": None}
            report.append(f"## TRIAL: {len(arms)} hook variant(s) of {clip} ready for Instagram Trial Reels")
json.dump(_var, open(_vp, "w"), indent=1, ensure_ascii=False)
os.makedirs(os.path.join(HERE, "reports"), exist_ok=True)
open(os.path.join(HERE, "reports", "latest.md"), "w").write("\n\n".join(report))
print("\n\n".join(report)[-4000:])
