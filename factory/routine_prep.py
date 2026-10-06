"""Prepare the weekly planning agent's reading (see factory/PLANNING.md).

Prints queue depth, fetches + decrypts the next unplanned transcripts (public
release URLs, TRANSCRIPT_KEY from the environment), writes 30-second reading
blocks, and lists next candidate episodes if the month's list is running out.

    python factory/routine_prep.py [--max 4]
"""
import json, os, re, subprocess, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
BASE = "https://github.com/kamaycampos/kt-machine/releases/download/sources/"
MAX = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 4
# WHOSE MACHINE IS THIS RUN FOR. Two accounts, two lists, two sets of plans, and
# a source is never allowed to serve both (factory/pipeline/kt_fence.py).
AR = "--brand" in sys.argv and sys.argv[sys.argv.index("--brand") + 1].lower() == "ar"
PLAN_FILE = "ar_source_plan.json" if AR else "source_plan.json"
MINE, THEIRS = ("ar_", "ep_") if AR else ("ep_", "ar_")
print(("AWAKENED RISE (Yaren)" if AR else "KAMAY") + " - reading " + PLAN_FILE)
WORK = os.path.join(ROOT, "work"); os.makedirs(WORK, exist_ok=True)
get = lambda n: urllib.request.urlopen(BASE + n, timeout=60).read()

man = json.load(open(os.path.join(ROOT, "state", "manifest.json")))["clips"]
queue = [c for c in man if not c.get("done") and not c.get("posted_at")
         and c["file"].startswith("AR_") == AR]
print(f"QUEUE: {len(queue)} clips waiting (~{len(queue) / 6:.1f} days at 6/day)")

try:                                   # what TikTok took down, so it gets replaced
    _h = json.load(open(os.path.join(ROOT, "state", "tiktok_history.json")))
    _gone = [g for g in _h.get("gone", []) if g["file"].startswith("AR_") == AR]
    if _gone:
        print(f"TAKEN DOWN BY TIKTOK ({len(_gone)}) - plan a replacement on the same episode, different angle:")
        for g in _gone[-8:]:
            print(f"  {g['file']}  (posted {g.get('posted')}, gone by {g.get('noticed')})")
except Exception:
    pass

idx = json.loads(get("sources_index.json"))

# SECOND CHANCES (6 Oct 2026). Every clip a gate refused is in plans/_failed.json
# with the gate's own words. Re-cut them FIRST: the episode is already transcribed
# and the teaching was already judged worth posting. A clip is offered at most
# MAX_TRIES times in all; one already re-cut (a plan clip with "retry_of") is not
# offered again until that re-cut has run.
MAX_TRIES = 3
try:
    _f = json.load(open(os.path.join(HERE, "plans", "_failed.json")))["clips"]
except (OSError, ValueError, KeyError):
    _f = {}
_plans = [json.load(open(os.path.join(HERE, "plans", f))) for f in os.listdir(os.path.join(HERE, "plans"))
          if f.endswith(".json") and not f.startswith("_")]
_recut = {c.get("retry_of") for q in _plans for c in q.get("clips", [])}
again = {}
for k, e in _f.items():
    if k.startswith(MINE) and e.get("tries", 1) < MAX_TRIES and k not in _recut:
        again.setdefault(e["source"][:-4], []).append((k, e))
if again:
    n = sum(len(v) for v in again.values())
    print(f"SECOND CHANCES: {n} clip(s) on {len(again)} episode(s) failed a gate - re-cut these FIRST "
          f"(PLANNING.md step 2c). Cues for each: work/<id>.srt")
    for v, items in sorted(again.items(), key=lambda kv: -len(kv[1])):
        print(f"  {v}  ({items[0][1]['plan']}, brand {items[0][1]['brand']})")
        for k, e in items:
            print(f"    {k}  in {e.get('in')} out {e.get('out')}  tries {e.get('tries', 1)}")
            print(f"      start '{e.get('start_words', '')}'  end '{e.get('end_words', '')}'")
            for w in e.get("why", [])[:2]:
                print(f"      WHY: {w[:220]}")
ALL = os.listdir(os.path.join(HERE, "plans"))
plans_txt = " ".join(open(os.path.join(HERE, "plans", f)).read() for f in ALL if f.endswith(".json"))
order = [e["id"] for e in json.load(open(os.path.join(HERE, PLAN_FILE)))["episodes"]]
ready = [v for v in order if v in idx and idx[v].get("transcript") and f'"{v}.mp4"' not in plans_txt]   # the month list only
print(f"READY TO PLAN: {len(ready)} episode(s); preparing {min(MAX, len(ready))}")
# the second-chance episodes' cues come too, after the new ones (they need only work/<id>.srt)
for v in ready[:MAX] + [v for v in again if v not in ready[:MAX] and v in idx and idx[v].get("transcript")]:
    open(f"/tmp/{v}.srt.enc", "wb").write(get(f"{v}.srt.enc"))
    srt = os.path.join(WORK, f"{v}.srt")
    r = subprocess.run(["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-pass", "env:TRANSCRIPT_KEY",
                        "-in", f"/tmp/{v}.srt.enc", "-out", srt], capture_output=True, text=True)
    if r.returncode:
        print(f"  {v}: cannot decrypt ({r.stderr.strip()[-80:]}) - skip"); continue
    cues = re.findall(r"(\d+):(\d+):(\d+)[,.](\d+) --> [^\n]+\n(.+?)(?:\n\n|\Z)", open(srt, errors="ignore").read(), re.S)
    blk = {}
    for h, m, s, _ms, t in cues:
        blk.setdefault((int(h) * 3600 + int(m) * 60 + int(s)) // 30 * 30, []).append(" ".join(t.split()))
    open(os.path.join(WORK, f"{v}_blocks.txt"), "w").write("\n".join(f"{k} {' '.join(blk[k])}" for k in sorted(blk)))
    e = idx[v]
    print(f"  {v}: '{e['title']}' {e.get('duration', 0) / 60:.0f} min -> work/{v}_blocks.txt (cues: work/{v}.srt)")

waiting = [v for v in order if v not in idx or not idx[v].get("transcript")]
print(f"MONTH LIST: {len(order)} episodes, {len(waiting)} not transcribed yet")
if len(order) - len([v for v in order if f'"{v}.mp4"' in plans_txt]) < 6:
    cat = json.load(open(os.path.join(HERE, "rumble_catalog.json")))
    series = json.load(open(os.path.join(HERE, "kt_series.json")))
    norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())[:40]
    used = {norm(os.path.splitext(s.get("source", ""))[0]) for s in series.values()}
    cands = [(e["date"], u, e) for u, e in cat.items() if not e["short"] and e["dur"] >= 1200 and e["height"] >= 1080
             and norm(e["title"]) not in used and re.search(r"/(v[a-z0-9]+)-", u)[1] not in order]
    extra = [v for v, e in idx.items() if v not in order and not e.get("test") and f'"{v}.mp4"' not in plans_txt
             and e.get("status") != "fetch_failed"]       # never downloaded: not stock
    print("ALREADY STOCKED, not in the month list:", ", ".join(f"{v} '{idx[v]['title'][:60]}'" for v in extra) or "none")
    print("CANDIDATES to append to source_plan.json - PICK HOUSE/PROPERTY EPISODES FIRST:")
    for d, u, e in sorted(cands, reverse=True)[:15]:
        print(f"  {re.search(r'/(v[a-z0-9]+)-', u)[1]} {d} {e['dur'] // 60}m {e['height']}p {e['title'][:80]}")
