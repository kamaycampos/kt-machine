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
# At most AGAIN episodes of second chances per run (6 Oct 2026). The first run after
# second chances shipped was handed the whole backlog since 23 Sept - 24 episodes for
# KT, 29 clips for AR - fanned out 21 agents and hit the account's usage limit with
# nothing pushed. The rest wait for the next daily run.
AGAIN = int(sys.argv[sys.argv.index("--again") + 1]) if "--again" in sys.argv else 3
SECOND_MIN_EP, SECOND_FREE = 30, 15     # second pass: episodes of 30+ min with 15+ unused min
second = {}                              # second-pass episode -> the clips already cut from it
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
# a refusal with no recorded words or reason cannot be diagnosed - never offer it
blind = {v: [(k, e) for k, e in items if not (e.get("why") and e.get("start_words"))] for v, items in again.items()}
again = {v: [(k, e) for k, e in items if e.get("why") and e.get("start_words")] for v, items in again.items()}
again = {v: items for v, items in again.items() if items}
n_blind = sum(len(v) for v in blind.values())
if n_blind:
    print(f"(second chances: {n_blind} refused clip(s) have no recorded reason or words - not offered)")
waiting = 0
if len(again) > AGAIN:
    keep = sorted(again, key=lambda v: -len(again[v]))[:AGAIN]
    waiting = len(again) - AGAIN
    again = {v: again[v] for v in keep}
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
    if waiting:
        print(f"  ({waiting} more episode(s) of second chances wait for the next run)")
ALL = os.listdir(os.path.join(HERE, "plans"))
plans_txt = " ".join(open(os.path.join(HERE, "plans", f)).read() for f in ALL if f.endswith(".json"))
order = [e["id"] for e in json.load(open(os.path.join(HERE, PLAN_FILE)))["episodes"]]
ready = [v for v in order if v in idx and idx[v].get("transcript") and f'"{v}.mp4"' not in plans_txt]   # the month list only
# THE NEWEST UPLOAD FIRST, THE SAME DAY (Kamay, 11 Oct 2026: "from the last video of kt
# take the most value of it and the most high quality clips to post it the same day as
# #1 priority"). The 7 Oct episode sat stocked and transcribed for four days because it
# was not on the month list. Any upload from the last 14 days, transcribed and never
# planned, goes to the top of Kamay's reading. Yaren's lane keeps her own list, and a
# source on her list is never offered here (kt_fence: one source, one person).
if not AR:
    _theirs = set()
    try:
        _theirs = {e["id"] for e in json.load(open(os.path.join(HERE, "ar_source_plan.json")))["episodes"]}
    except (OSError, ValueError, KeyError):
        pass
    _cut = __import__("datetime").datetime.utcnow() - __import__("datetime").timedelta(days=14)
    # Kevin's publish date comes from the Rumble catalogue. sources_index "uploaded" is
    # when WE stocked it - an old episode stocked yesterday is not new.
    _pub = {}
    for _u, _e in json.load(open(os.path.join(HERE, "rumble_catalog.json"))).items():
        _m = re.search(r"/(v[a-z0-9]+)-", _u)
        if _m and not _e.get("short"):
            _pub[_m[1]] = _e.get("date", "")
    fresh = sorted((v for v, e in idx.items()
                    if e.get("transcript") and not e.get("test") and v not in _theirs
                    and _pub.get(v, "") >= _cut.strftime("%Y-%m-%d")
                    and f'"{v}.mp4"' not in plans_txt),
                   key=lambda v: _pub[v], reverse=True)
    if fresh:
        print("NEWEST UPLOADS - PLAN THESE FIRST (same-day rule): " + ", ".join(
            f"{v} '{idx[v]['title'][:50]}' (published {_pub[v]})" for v in fresh))
    ready = fresh + [v for v in ready if v not in fresh]
    # NEVER AN EMPTY RUN WHILE TRANSCRIBED EPISODES SIT UNUSED (14 Oct 2026). The month list
    # was used up, "READY TO PLAN: 0", and the planner spent three days only re-cutting
    # refused clips while 40+ downloaded, transcribed episodes were never offered. Top up
    # from those, newest first. The planner still applies every PLANNING.md skip rule.
    if len(ready) < MAX:
        _spare = sorted((v for v, e in idx.items()
                         if e.get("transcript") and not e.get("test") and v not in _theirs
                         and v not in ready and f'"{v}.mp4"' not in plans_txt),
                        key=lambda v: _pub.get(v, ""), reverse=True)
        if _spare:
            print(f"MONTH LIST USED UP - also ready (stocked, transcribed, never planned): {len(_spare)}")
        ready += _spare[:MAX - len(ready)]
    # SECOND PASS (16 Oct 2026). An episode was "done" once planned, after 6-9 clips. KT's
    # 37 planned episodes run 1,295 minutes and their plans touch 302 of them; a full read
    # of two long interviews found 8 and 10 new arcs in the unused minutes, as strong as
    # the first pick. So once new episodes run short, go back to an HD episode for arcs no
    # clip has used. check_plan.py refuses any clip that re-uses another clip's minutes.
    # Never while a clip of that source is still waiting to post or to be built: a new
    # folder of the same video must not stack a third post on its day (RULES #21).
    if len(ready) < MAX:
        _named = {f[:-5]: json.load(open(os.path.join(HERE, "plans", f))) for f in os.listdir(os.path.join(HERE, "plans"))
                  if f.endswith(".json") and not f.startswith("_")}
        try:
            _built = set(json.load(open(os.path.join(HERE, "plans", "_done.json"))))
        except (OSError, ValueError):
            _built = set()
        _src = {q["brand"]: q["source"][:-4] for q in _named.values()}
        _busy = ({_src.get(c["file"].split("/")[0]) for c in queue} | set(again)
                 | {q["source"][:-4] for k, q in _named.items() if k not in _built})
        _fenced = {q["source"][:-4] for k, q in _named.items() if k.startswith(THEIRS)} | _theirs
        _used = {}
        for k, q in _named.items():
            if k.startswith(MINE):
                _used.setdefault(q["source"][:-4], []).extend((float(c["in"]), float(c["out"]), c["slug"]) for c in q["clips"])
        def _free(v):
            t, end = 0.0, 60.0                     # the first minute is the intro
            for a, b, _s in sorted(_used[v]):
                t += max(0.0, a - end); end = max(end, b)
            return t + max(0.0, idx[v].get("duration", 0) - 60 - end)
        _cand = sorted(((_free(v), v) for v in _used
                        if v in idx and idx[v].get("transcript") and idx[v].get("height", 0) >= 1080
                        and idx[v].get("duration", 0) >= SECOND_MIN_EP * 60
                        and v not in _busy and v not in _fenced and v not in ready), reverse=True)
        _cand = [(t, v) for t, v in _cand if t >= SECOND_FREE * 60]
        if _cand:
            print(f"SECOND PASS - {len(_cand)} HD episode(s) already cut hold {sum(t for t, _ in _cand) / 3600:.1f} h "
                  f"no clip has used. Plan NEW arcs from these after the new episodes (PLANNING.md 'SECOND PASS'):")
        for t, v in _cand[:MAX - len(ready)]:
            second[v] = sorted(_used[v])
            print(f"  {v} '{idx[v]['title'][:50]}' {idx[v]['duration'] / 60:.0f} min, {t / 60:.0f} min unused, "
                  f"{len(second[v])} clips already cut - write factory/plans/ep_{v}_p2.json (_p3 if taken)")
        ready += list(second)
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
    blk, shown = {}, []
    for h, m, s, _ms, t in cues:
        x = int(h) * 3600 + int(m) * 60 + int(s)
        # a second pass reads only what no clip has used; the used stretches are one line each
        cut = next((c for c in second.get(v, []) if c[0] - 2 <= x <= c[1]), None)
        if cut:
            if cut not in shown:
                shown.append(cut)
                blk.setdefault(x // 30 * 30, []).append(f"=== USED by {cut[2]} ({cut[0]:.0f}-{cut[1]:.0f}s): taken, never cut inside ===")
            continue
        blk.setdefault(x // 30 * 30, []).append(" ".join(t.split()))
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
    # THE OTHER ACCOUNT'S LIST IS NEVER A CANDIDATE (14 Oct 2026). Her list ran dry on
    # 12 Oct and this block offered episodes from his list too, under his file name and
    # his "house episodes first" hint - so her planner extended nothing, and her queue
    # sat at zero while the planner only re-cut old refusals.
    try:
        _other = {e["id"] for e in json.load(open(os.path.join(
            HERE, "source_plan.json" if AR else "ar_source_plan.json")))["episodes"]}
    except (OSError, ValueError, KeyError):
        _other = set()
    # An episode he named may be short; one stocked by hand for a list may be too.
    # Listed episodes only need to hold a clip (rumble_stock.py takes 3 min and up).
    cands = [(e["date"], u, e) for u, e in cat.items() if not e["short"] and e["dur"] >= 300 and e["height"] >= 1080
             and norm(e["title"]) not in used and re.search(r"/(v[a-z0-9]+)-", u)[1] not in order
             and re.search(r"/(v[a-z0-9]+)-", u)[1] not in _other
             and f'"{re.search(r"/(v[a-z0-9]+)-", u)[1]}.mp4"' not in plans_txt]
    extra = [v for v, e in idx.items() if v not in order and v not in _other and not e.get("test")
             and f'"{v}.mp4"' not in plans_txt
             and e.get("status") not in ("fetch_failed", "rejected")]       # never downloaded: not stock
    print("ALREADY STOCKED, not in the month list:", ", ".join(f"{v} '{idx[v]['title'][:60]}'" for v in extra) or "none")
    if AR:
        print(f"MONTH LIST RUNNING OUT - APPEND 6 to {PLAN_FILE} (AR_PLANNING.md step 2d). HER LANE ONLY: "
              "prayer, the Brotherhood, the subconscious, energy, meditation, manifesting, disclosure. "
              "Never money, health or politics. Stocked ones above can be planned on the next run.")
    else:
        print(f"CANDIDATES to append to {PLAN_FILE} - PICK HOUSE/PROPERTY EPISODES FIRST:")
    for d, u, e in sorted(cands, reverse=True)[:25 if AR else 15]:
        print(f"  {re.search(r'/(v[a-z0-9]+)-', u)[1]} {d} {e['dur'] // 60}m {e['height']}p {e['title'][:80]}")
