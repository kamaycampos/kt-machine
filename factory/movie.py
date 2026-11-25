#!/usr/bin/env python3
"""THE DAILY MOVIE CLIP, AUTOMATIC (14 Nov 2026).

Kamay, 13-14 Nov: about ONE movie clip a day - a real Kevin story with generated moving scenes
that show what he says at that second, its OWN calm music, gentle sound effects, his end card -
and it "posts by itself, no approval". Until today a movie clip was a hand-written Episode spec
full of word numbers nobody but a person at a screen could write.

Now the planner writes a small MOVIE PLAN in Kevin's own words (factory/movies/mv_*.json):

  source, in, out            the stretch of the episode (seconds, from the transcript)
  start_words, end_words     his first and last words (or "keep": [[first words, last words], ..]
                             to tell the story in pieces)
  scenes [{on, gen, move}]   on = the EXACT words he says while the scene shows; gen = the picture
                             (only what those words say; stand-ins, never a real person's name);
                             move = what moves in it. 5 to 8 scenes, the first on the first words.
  big [..], italic [..]      his words written large / in italics;  payoff = where every word goes large
  fix {"heard": "Shown"}     a word the transcript mis-heard
  mood [..]                  what the music should feel like
  title, hook [l1, l2], caption (opens with Comment "WISH", holds the token {episode}), send

and this file does the rest, on GitHub's servers (.github/workflows/movie.yml):

  python factory/movie.py check  <plan>     the planner's own check (also the merge door's)
  python factory/movie.py pick              which plan is next + which scenes still have to be made
  python factory/movie.py spec   <plan>     time his words, turn the plan into an Episode spec
  python factory/movie.py gate   <plan>     look at what was built; refuse a clip that is not a movie
  python factory/movie.py queue  <plan>     cover + upload
  python factory/movie.py enter  <plan>     into the posting queue: one solo post a day at 12:30 pm New York

A scene is made once and kept beside the spec. A plan whose scenes could not be made today is
tried again tomorrow (the scenes that worked are already there), three days at most.
"""
import difflib
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
K = os.path.expanduser("~/Kamay")
MOVIES = os.path.join(HERE, "movies")
DONE = os.path.join(MOVIES, "_done.json")
EPISODES = os.path.join(HERE, "episodes")
MUSIC = os.path.join(HERE, "music")
OUT = os.environ.get("PREVIEW_OUT", "/tmp/previews")
FF = os.path.join(K, "bin", "ffmpeg") if os.path.exists(os.path.join(K, "bin", "ffmpeg")) else "ffmpeg"
REPO = os.environ.get("GITHUB_REPOSITORY", "kamaycampos/kt-machine")

POST_AT = "12:30"            # New York. Our own 304 KT reels: the 12-2 pm block is the best one.
RUNWAY = 2                   # movie clips kept waiting, at most (one posts a day)
MAX_TRIES = 3
MIN_SCENES, MAX_SCENES = 5, 8          # 19 Nov: was 3-4 - Episode 6 showed 14 s of story pictures in 138 s.
                                       # Every scene is made on its own server (own free allowance), so 8 fit.
MIN_SHOWN = 4                # fewer generated scenes on screen than this = not a movie, not queued
MIN_SECS, MAX_SECS = 50.0, 110.0  # 22 Nov: the 40-65 s cap of 19 Nov cut Episodes 8 and 10 to 41 / 46 s and the
                                  # want and the result were what fell out. The five beats decide (PLANNING.md
                                  # "WHAT AN EPISODE IS"); ONE-GINSU-AD ran 162 s and was watched 52.6 s on average.
SCENE_MIN, SCENE_MAX = 2.2, 3.2        # a generated scene is 3.5 s long
# The words Meta's rule and our bot both answer on KT, and the line each one may promise.
# Only what Kamay has confirmed is here (14 Nov: WISH = all 14 audios + the ebook, free).
OFFERS = {"WISH": "Or get them here now, free: https://freeyourwish.kevintrudeau.com/?ref=a43c8j"}
# Never a real person's face (generators refuse it, and it misleads): no names in a picture.
NO_NAMES = re.compile(r"\b(kevin|trudeau|trump|oprah|elon|musk|bezos|gates|rockefeller|carnegie|jordan|"
                      r"buffett|obama|biden|clinton|gorbachev|schwarzkopf|schwartzkopf|jesus|pope)\b", re.I)


def norm(w):
    return re.sub(r"[^a-z0-9]", "", str(w).lower().replace("’", "'"))


def toks(s):
    return [t for t in (norm(x) for x in str(s).split()) if t]


def find(words_n, phrase, lo=0, hi=None, last=False):
    """Where his words hold this phrase: (first index, last index) or None. The transcript the
    planner read and the timing pass do not spell everything alike ("$1,500" / "1500 dollars"),
    so a near match counts; an exact one always wins."""
    p = toks(phrase)
    hi = len(words_n) if hi is None else min(hi, len(words_n))
    if not p or hi - lo < 1:
        return None
    need = 0.9 if len(p) == 1 else 0.78
    cands = []                                   # (ratio, first, last)
    for n in sorted({len(p), len(p) - 1, len(p) + 1, len(p) + 2} - {0}, key=lambda x: abs(x - len(p))):
        for i in range(lo, hi - n + 1):
            win = words_n[i:i + n]
            if win[0] != p[0] and difflib.SequenceMatcher(None, win[0], p[0]).ratio() < 0.6:
                continue
            r = difflib.SequenceMatcher(None, " ".join(win), " ".join(p)).ratio()
            if r >= need:
                cands.append((r, i, i + n - 1))
    if not cands:
        return None
    top = max(c[0] for c in cands)
    good = [c for c in cands if c[0] >= top - 0.03]
    r, i0, i1 = max(good, key=lambda c: (c[1], c[0])) if last else min(good, key=lambda c: (c[1], -c[0]))
    return (i0, i1)


def load(path):
    p = json.load(open(path))
    p.setdefault("slug", os.path.basename(path)[:-5])
    return p


def done():
    try:
        return json.load(open(DONE))
    except (OSError, ValueError):
        return {"next_episode": 3, "built": {}, "tries": {}, "music": []}


def scene_file(slug, sc):
    h = hashlib.md5((sc["gen"] + "|" + sc.get("move", "")).encode()).hexdigest()[:10]
    return os.path.join(EPISODES, slug, f"g_{h}.mp4")


def srt_words(vid, a, b):
    """His words between a and b from the planner's transcript, if this machine has it."""
    for d in (os.path.join(ROOT, "work"), os.path.join(K, "work")):
        f = os.path.join(d, vid + ".srt")
        if os.path.exists(f):
            out = []
            for m in re.finditer(r"(\d\d):(\d\d):(\d\d)[,.]\d+ --> (\d\d):(\d\d):(\d\d)[,.]\d+\n(.*?)(?:\n\n|\Z)",
                                 open(f, encoding="utf-8", errors="ignore").read(), re.S):
                t0 = int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3])
                t1 = int(m[4]) * 3600 + int(m[5]) * 60 + int(m[6])
                if t1 >= a - 8 and t0 <= b + 8:
                    out += toks(m[7])
            return out
    return None


# ------------------------------------------------------------------------------------- check
def check(path):
    p, bad = load(path), []
    say = bad.append
    if not re.fullmatch(r"mv_v[a-z0-9]+_[a-z0-9_]{3,40}", p["slug"]):
        say("file name must be mv_<episode id>_<short_name>.json (small letters, digits, _)")
    for k in ("source", "in", "out", "title", "hook", "caption", "scenes", "send", "mood"):
        if not p.get(k):
            say(f"missing '{k}'")
    if bad:
        return bad
    vid = p["source"].replace(".mp4", "")
    if not p["slug"].startswith(f"mv_{vid}_"):
        say("the file name's episode id is not the plan's source")
    a, b = float(p["in"]), float(p["out"])
    if not 60 <= b - a <= 260:
        say(f"the stretch is {b - a:.0f}s: a movie clip reads 60-260 s of the episode (it is tightened to {MIN_SECS:.0f}-{MAX_SECS:.0f})")
    # AN EPISODE IS A RESULT STORY (22 Nov 2026, Kamay: "the happiest inmate ... so horrible"; ONE GINSU AD
    # "the perfect example"). Episodes 4, 8, 9 had a place, people and a turn - and no result, so nobody
    # watching wanted the method. The planner's check is the factory's check (RULES 27): no counted result
    # or no answers to the three questions = not an Episode.
    if not (p.get("money") or p.get("names")):
        say("an Episode is a RESULT story: 'money' (a sum he says) or 'names' (the thing he got) must not be empty "
            "- a story whose turn is a feeling (happy, amazed, calm) is an ordinary clip, not an Episode")
    # NOT KEVIN'S CAMERA (25 Nov 2026): Episode 11 was built from v5hsmvp, a split screen with a radio host's face
    # filling two thirds and Kevin small at the side - the factory had already refused 3 clips of it as "not Kevin".
    try:
        _fl = json.load(open(os.path.join(HERE, "plans", "_failed.json")))["clips"]
        _nk = sum(1 for _e in _fl.values() if str(_e.get("source", ""))[:-4] == vid
                  and any("not Kevin" in w for w in (_e.get("why") or [])))
    except (OSError, ValueError, KeyError):
        _nk = 0
    if _nk >= 2:
        say(f"{vid} is not Kevin's camera ({_nk} clips of it refused 'not Kevin' - a split screen or a guest): pick another episode")
    _why = str(p.get("why_movie", ""))
    for _q in ("RESULT:", "METHOD:", "WISH:"):
        if _q not in _why:
            say(f"why_movie must answer {_q} (PLANNING.md 'WHAT AN EPISODE IS': the result he got, how his mind / a "
                "decision / a technique did it, why a stranger would want the audios after this story)")
    if re.search(r"\b(prison|inmate|warden|jail|monk|guru)\b", str(p.get("title", "")) + " " + " ".join(map(str, p.get("hook") or [])), re.I):
        say("never an Episode: prison life, monks, gurus (22 Nov) - write it as an ordinary clip or pick a result story")
    if not (p.get("keep") or (p.get("start_words") and p.get("end_words"))):
        say("give start_words + end_words, or keep [[first words, last words], ..]")
    sc = p["scenes"]
    if not MIN_SCENES <= len(sc) <= MAX_SCENES:
        say(f"{len(sc)} scenes: write {MIN_SCENES} to {MAX_SCENES} - a story picture every 6-8 seconds")
    # THE COLD OPEN (19 Nov 2026, Kamay: "the suspense, the emotion"). Theirs opens on a scene of
    # the story ("I WAS...", a boy in a chandelier hall); ours opened on Kevin at a desk mid-sentence.
    _first = (p.get("keep") or [[p.get("start_words", "")]])[0][0]
    if sc and toks(_first)[:3] and toks(sc[0].get("on", ""))[:3] != toks(_first)[:3]:
        say("scene 1 must play on the clip's first words (open on the story, not on the desk): "
            f"its 'on' starts with \"{_first}\"")
    for i, s in enumerate(sc, 1):
        for k in ("on", "gen", "move"):
            if not s.get(k):
                say(f"scene {i}: missing '{k}'")
        if len(str(s.get("gen", "")).split()) < 12:
            say(f"scene {i}: the picture needs 12+ words (who, where, when, what they are doing)")
        if len(toks(s.get("on", ""))) < 4:
            say(f"scene {i}: 'on' must be 4+ of his exact words")
        m = NO_NAMES.search(str(s.get("gen", "")) + " " + str(s.get("move", "")))
        if m:
            say(f"scene {i}: no real person's name in a picture ('{m[0]}') - describe a stand-in")
    if not (isinstance(p["hook"], list) and len(p["hook"]) == 2):
        say("hook = [line one, line two] (the cover's headline)")
    cap = p["caption"]
    key = (p.get("cta_keyword") or "WISH").upper()
    if key not in OFFERS:
        say(f"cta_keyword {key}: only {', '.join(OFFERS)} is confirmed to deliver what a movie clip's end card promises")
    if not cap.startswith(f'Comment "{key}"'):
        say(f'the caption opens with: Comment "{key}" ...')
    if "{episode}" not in cap:
        say("the caption must hold the token {episode} on its own line (it becomes 'Episode N: Title.')")
    if re.search(r"\bcures?\b|link below", cap, re.I):
        say("caption: never 'cure', never 'link below'")
    if "link in my bio" not in cap:
        say("caption: end with the safety line - 'No message within a minute? Look in your message requests, or use the link in my bio.'")
    if len(cap) > 2100 or len(re.findall(r"#\w+", cap)) > 6:
        say("caption: 2,100 characters and 6 hashtags at most")
    d = done()
    if p["slug"] in d["built"]:
        say("this movie plan was already built")
    tr = srt_words(vid, a, b)
    if tr is None:
        print(f"  (no transcript of {vid} on this machine: his words are checked when the clip is timed)")
    else:
        phrases = [("start_words", p.get("start_words")), ("end_words", p.get("end_words")), ("payoff", p.get("payoff"))]
        phrases += [(f"keep {i}", x) for i, kp in enumerate(p.get("keep") or [], 1) for x in kp]
        phrases += [(f"scene {i} on", s.get("on")) for i, s in enumerate(sc, 1)]
        phrases += [("big", x) for x in p.get("big") or []] + [("italic", x) for x in p.get("italic") or []]
        phrases += [("money", x) for x in p.get("money") or []]
        phrases += [("names", x.get("say") if isinstance(x, dict) else x) for x in p.get("names") or []]
        for name, ph in phrases:
            if ph and not find(tr, ph):
                say(f"{name}: he does not say \"{ph}\" between {a:.0f} and {b:.0f} s")
    return bad


# -------------------------------------------------------------------------------------- pick
def waiting_solos():
    man = json.load(open(os.path.join(ROOT, "state", "manifest.json")))["clips"]
    return [c for c in man if c.get("solo") and not c.get("done") and not c.get("posted_at")
            and not c["file"].startswith("AR_")]


def pick(only=None):
    d = done()
    plans = sorted(glob.glob(os.path.join(MOVIES, "mv_*.json")), key=os.path.getmtime)
    todo = [f for f in plans if os.path.basename(f)[:-5] not in d["built"]
            and d["tries"].get(os.path.basename(f)[:-5], 0) < MAX_TRIES]
    if only:
        todo = [f for f in plans if os.path.basename(f)[:-5] == only]
    out = {"slug": "", "scenes": [], "count": 0}
    if not todo:
        print("no movie plan waiting")
    elif not only and len(waiting_solos()) >= RUNWAY:
        print(f"{len(waiting_solos())} movie clip(s) already waiting to post: nothing to build today")
    else:
        # the plan that already has scenes made comes first (finish what was started)
        todo.sort(key=lambda f: -len(glob.glob(os.path.join(EPISODES, os.path.basename(f)[:-5], "g_*.mp4"))))
        p = load(todo[0])
        bad = check(todo[0]) if p["slug"] not in d["built"] else []
        if bad:
            print("REFUSED", p["slug"], *bad, sep="\n  ")
            d["tries"][p["slug"]] = MAX_TRIES
            json.dump(d, open(DONE, "w"), indent=1)
        else:
            out["slug"] = p["slug"]
            out["count"] = 1
            for i, s in enumerate(p["scenes"]):
                f = scene_file(p["slug"], s)
                if not (os.path.exists(f) and os.path.getsize(f) > 20000):
                    out["scenes"].append({"n": i + 1, "name": os.path.basename(f), "gen": s["gen"], "move": s["move"]})
            print(f"NEXT MOVIE: {p['slug']} - {len(out['scenes'])} of {len(p['scenes'])} scene(s) still to make")
    gh = os.environ.get("GITHUB_OUTPUT")
    if gh:
        with open(gh, "a") as fh:
            fh.write(f"slug={out['slug']}\ncount={out['count']}\nnscenes={len(out['scenes'])}\n"
                     f"matrix={json.dumps({'include': out['scenes']})}\n")
    return out


# -------------------------------------------------------------------------------------- spec
def moving(path):
    """A generated scene is a MOVIE only if something in it moves and it is not a black frame
    (Kamay, 13 Nov: a still with a camera push is not a movie)."""
    fr = []
    for t in ("0.3", "2.6"):
        r = subprocess.run([FF, "-loglevel", "error", "-ss", t, "-i", path, "-frames:v", "1", "-vf", "scale=96:54,format=gray",
                            "-f", "rawvideo", "-"], capture_output=True)
        fr.append(r.stdout)
    if len(fr[0]) != 96 * 54 or len(fr[1]) != 96 * 54:
        return False, "unreadable"
    mean = sum(fr[0]) / len(fr[0])
    diff = sum(abs(x - y) for x, y in zip(fr[0], fr[1])) / len(fr[0])
    ok = mean > 14 and diff > 1.2
    return ok, f"brightness {mean:.0f}, movement {diff:.1f}"


def pick_music(p, d):
    """The track that fits THIS story (factory/music_pick.py): what Kevin's own words are about,
    the planner's mood, never the last track used."""
    import music_pick
    text = " ".join(" ... ".join(k) for k in (p.get("keep") or [])) + " " + p.get("start_words", "") + " " + \
        " ".join(s_.get("on", "") + " " + s_.get("gen", "") for s_ in p["scenes"]) + " " + p.get("title", "")
    # "music": "none" in a plan = this clip goes out with his voice alone (15 Nov 2026, Kamay on
    # the first two tracks the matcher chose: "THE MUSIC IS A NO NO ... we either fine tune on
    # what is the ideal music for it and you find it, or we post it without nothing").
    # "music": "<file in factory/music/>" = that track, chosen by a person.
    if str(p.get("music", "")).lower() == "none":
        return None
    if p.get("music") and os.path.exists(os.path.join(MUSIC, p["music"])):
        return p["music"]
    used = list(d.get("music", []))
    if p["slug"] in d["built"] and used:
        used = used[:-1]                       # a rebuild: its own earlier track is not "the last one used"
    return music_pick.pick(text, p.get("mood") or (), used)


def spec(path):
    p = load(path)
    slug, vid = p["slug"], p["source"].replace(".mp4", "")
    edir = os.path.join(EPISODES, slug)
    os.makedirs(edir, exist_ok=True)
    sp_path = os.path.join(edir, "spec.json")
    stub = {"slug": slug, "vid": vid, "t_in": float(p["in"]) - 1.5, "t_out": float(p["out"]) + 2.5}
    json.dump(stub, open(sp_path, "w"), indent=1)
    r = subprocess.run([sys.executable, os.path.join(HERE, "episode_build.py"), sp_path, "list"])
    wf = os.path.join(OUT, f"{slug}_words.json")
    if r.returncode or not os.path.exists(wf):
        raise SystemExit("MOVIE FAILED: his words could not be timed")
    words = json.load(open(wf))
    wn = [norm(w[2]) for w in words]
    notes = []

    def need(name, ph, **kw):
        hit = find(wn, ph, **kw)
        if not hit:
            notes.append(f"{name}: \"{ph}\" not found in the timed words")
        return hit

    keeps = []
    if p.get("keep"):
        lo = 0
        for i, (first, last) in enumerate(p["keep"], 1):
            x = need(f"keep {i} first", first, lo=lo)
            y = need(f"keep {i} last", last, lo=x[0] if x else lo)
            if x and y and y[1] >= x[0]:
                keeps.append([x[0], y[1]])
                lo = y[1] + 1
    else:
        x = need("start_words", p["start_words"])
        y = need("end_words", p["end_words"], lo=x[0] if x else 0, last=True)
        if x and y:
            keeps.append([x[0], y[1]])
    if not keeps:
        raise SystemExit("MOVIE FAILED: " + "; ".join(notes))
    inside = lambda i: any(a <= i <= b for a, b in keeps)
    piece_end = lambda i: next(b for a, b in keeps if a <= i <= b)

    scenes = []
    for n, s in enumerate(p["scenes"], 1):
        hit = None
        for a, b in keeps:                                     # his words, inside what is kept
            hit = find(wn, s["on"], lo=a, hi=b + 1)
            if hit:
                break
        if not hit:
            notes.append(f"scene {n}: \"{s['on']}\" is not in the kept words - scene left out")
            continue
        i0, i1 = hit
        while words[i1][1] - words[i0][0] < SCENE_MIN and i1 < piece_end(i0):
            i1 += 1
        piece_start = next(a for a, b in keeps if a <= i0 <= b)
        while words[i1][1] - words[i0][0] < SCENE_MIN and i0 > piece_start \
                and not (scenes and i0 - 1 <= scenes[-1]["to"]):
            i0 -= 1                                            # the piece ends here: start a little sooner
        while words[i1][1] - words[i0][0] > SCENE_MAX and i1 > i0 + 2:
            i1 -= 1
        if scenes and i0 <= scenes[-1]["to"]:
            notes.append(f"scene {n}: overlaps the scene before it - left out")
            continue
        f = scene_file(slug, s)
        if os.path.exists(f) and os.path.getsize(f) > 20000:
            ok, why = moving(f)
            print(f"  scene {n} {os.path.basename(f)}: {why} -> {'ok' if ok else 'NOT a moving scene, deleted'}")
            if not ok:
                os.remove(f)
        scenes.append({"src": {"gen": s["gen"], "move": s["move"]}, "from": i0, "to": i1, "start": 0.1})

    voices, joins = {}, []

    def mark(phrases, v, every=False):
        for ph in phrases or []:
            lo = 0
            while True:
                hit = None
                for a, b in keeps:
                    if b < lo:
                        continue
                    hit = find(wn, ph, lo=max(a, lo), hi=b + 1)
                    if hit:
                        break
                if not hit:
                    if lo == 0:
                        notes.append(f"{v}: \"{ph}\" not found")
                    break
                for i in range(hit[0], hit[1] + 1):
                    voices[str(i)] = v
                if hit[1] > hit[0] and hit[1] - hit[0] <= (3 if v[0] in 'GN' else 2):
                    joins.append([hit[0], hit[1]])
                lo = hit[1] + 1
                if not every:
                    break

    mark(p.get("italic"), "I")
    mark(p.get("big"), "X", every=True)
    # A SUM OF MONEY is gold; over a scene it sits at the top of the picture, as theirs does.
    # THE THING HE NAMES is written across the picture in colour (15 Nov 2026, episode_build VOICE).
    in_scene = lambda i: any(sc["from"] <= i <= sc["to"] for sc in scenes)
    mark(p.get("money"), "G", every=True)
    for k_, v_ in list(voices.items()):
        if v_ == "G" and in_scene(int(k_)):
            voices[k_] = "G@T"
    for nm in p.get("names") or []:
        say, col = (nm.get("say"), nm.get("color", "red")) if isinstance(nm, dict) else (nm, "red")
        mark([say], "N:" + col)
    joins = [j for k, j in enumerate(joins) if not any(j[0] <= o[1] and o[0] <= j[1] for o in joins[:k])]
    fix = {}
    for heard, shown in (p.get("fix") or {}).items():
        for i, w in enumerate(wn):
            if w == norm(heard) and inside(i):
                fix[str(i)] = shown
    out = dict(stub, keeps=keeps, scenes=scenes, voices=voices, join=joins, fix=fix, tighten=0.85,
               cap_y=800, end_card="end_kamay.png", end_secs=4.0, music_db=-27, fx=True, fx_db=-31,
               post={"title": p["title"]},
               title_top={"tag": f"EPISODE {int((done()['built'].get(slug) or {}).get('episode') or done()['next_episode'])}",
                          "line": p["title"]})
    if p.get("payoff"):
        hit = find(wn, p["payoff"], lo=keeps[-1][0], hi=keeps[-1][1] + 1, last=True)
        if hit:
            out["big_from"] = hit[0]
        else:
            notes.append(f"payoff: \"{p['payoff']}\" not found")
    d = done()
    track = pick_music(p, d)
    if track:
        out["music"] = track
    else:
        out["fx"] = False                      # no bed: no effects either, his voice alone
    shutil.copy(os.path.join(HERE, "assets", "end_kamay.png"), os.path.join(edir, "end_kamay.png"))
    json.dump(out, open(sp_path, "w"), indent=1)
    json.dump({"notes": notes, "music": track, "planned_scenes": len(p["scenes"]), "placed_scenes": len(scenes)},
              open(os.path.join(OUT, f"{slug}_movie.json"), "w"), indent=1)
    print(f"MOVIE SPEC {slug}: {len(keeps)} piece(s), {len(scenes)} scene(s) placed, {len(voices)} large/italic words, music {track}")
    for n_ in notes:
        print("  note:", n_)


# -------------------------------------------------------------------------------------- gate
def gate(path):
    p = load(path)
    slug = p["slug"]
    d = done()
    info_f = os.path.join(OUT, f"{slug}_info.json")
    film = os.path.join(OUT, f"{slug}_9x16.mp4")
    bad = []
    if not (os.path.exists(info_f) and os.path.exists(film)):
        bad.append("the builder made no file")
        info = {}
    else:
        info = json.load(open(info_f))
        if not MIN_SECS <= info["seconds"] <= MAX_SECS:
            bad.append(f"{info['seconds']:.0f}s long (a movie clip is {MIN_SECS:.0f}-{MAX_SECS:.0f}s)")
        shown = info.get("scenes", 0)
        if shown < MIN_SHOWN:
            bad.append(f"only {shown} generated scene(s) on screen: under {MIN_SHOWN} it is not a movie clip")
        # no music is allowed (15 Nov 2026): only a track Kamay approved by ear may be under a clip
        if not info.get("end_card"):
            bad.append("no end card")
    d["tries"][slug] = d["tries"].get(slug, 0) + (1 if bad else 0)
    json.dump(d, open(DONE, "w"), indent=1)
    if bad:
        left = MAX_TRIES - d["tries"][slug]
        print(f"MOVIE NOT QUEUED {slug}:", *bad, sep="\n  ")
        print(f"  the scenes that were made are kept; {'tried again on the next run' if left > 0 else 'retired after ' + str(MAX_TRIES) + ' tries'}")
        return 1
    print(f"MOVIE PASSED {slug}: {info['seconds']:.0f}s, {info['scenes']} scenes, music {info['music']}")
    return 0


# ------------------------------------------------------------------------------------- queue
def next_slot(man):
    """12:30 pm New York on the first day from tomorrow that has no solo clip."""
    from zoneinfo import ZoneInfo
    taken = {(c.get("posted_at") or c.get("scheduled_at") or "")[:10] for c in man if c.get("solo")}
    day = datetime.now(ZoneInfo("America/New_York")).date() + timedelta(days=1)
    while day.isoformat() in taken:
        day += timedelta(days=1)
    return f"{day.isoformat()}T{POST_AT}"


def queue(path):
    p = load(path)
    slug = p["slug"]
    d = done()
    info = json.load(open(os.path.join(OUT, f"{slug}_info.json")))
    film = os.path.join(OUT, f"{slug}_9x16.mp4")
    # A REBUILD OF A CLIP THAT IS STILL WAITING keeps its Episode number and its file name, so the
    # new film simply takes the old one's place in the queue (15 Nov 2026).
    was = d["built"].get(slug) or {}
    n = int(was.get("episode") or d["next_episode"])
    name = re.sub(r"[^A-Z0-9]+", "-", p["title"].upper()).strip("-")[:48]
    rel = was.get("file") or f"KT_EPISODE/{n:02d}_{name}_{round(info['seconds'])}s.mp4"
    stem = os.path.join(OUT, rel.replace("/", "--")[:-4])
    shutil.copy(film, stem + ".mp4")
    # the cover: a movie poster from the first scene that is on screen
    sys.path.insert(0, HERE)
    covers = []
    try:
        import poster
        # the picture of the THING the story is about: the scene the plan names ("poster": 2),
        # else the first scene
        k_ = int(p.get("poster", 1)) - 1
        want = scene_file(slug, p["scenes"][k_ if 0 <= k_ < len(p["scenes"]) else 0]) + ".src"
        still = want if os.path.exists(want) else next(
            (s for s in sorted(glob.glob(os.path.join(EPISODES, slug, "g_*.mp4.src")), key=os.path.getmtime)), None)
        if not still:
            still = stem + "_frame.jpg"
            subprocess.run([FF, "-y", "-loglevel", "error", "-ss", "1.0", "-i", os.path.join(OUT, f"{slug}.mp4"),
                            "-frames:v", "1", still])
        if os.environ.get("EP_LOOK", "cosmos") == "film":
            c, t = poster.make(still, f"EPISODE {n}", p["title"], stem)
        else:                                   # the cosmos look (25 Nov 2026, factory/cosmos.py)
            import cosmos
            c, t = cosmos.cover(still, f"EPISODE {n}", p["title"], stem)
        covers = [f for f in (c, t) if f and os.path.exists(f)]
    except Exception as e:
        print("cover failed:", type(e).__name__, e)
    # NO MOVIE CLIP WITHOUT ITS COVER (15 Nov 2026, Kamay: "make sure all movie clips get their
    # cover"). The poster is what the grid shows and what he adds by hand; a clip whose cover
    # could not be made is not queued - the next run tries again.
    if len(covers) < 2:
        raise SystemExit("MOVIE NOT QUEUED: its cover could not be made")
    if os.environ.get("MOVIE_TEST"):
        print(f"TEST BUILD: {rel} stays in the previews release, nothing queued")
        return 0
    sys.path.insert(0, ROOT)
    import media_store
    gh = shutil.which("gh") or os.path.join(K, "bin", "gh")
    store = media_store.Store(gh, REPO)
    tag = store.room(2 + len(covers))
    if was:                                    # the replacement goes where the old film is
        _m = json.load(open(os.path.join(ROOT, "state", "manifest.json")))["clips"]
        tag = next((c.get("media_tag", "media") for c in _m if c["file"] == rel), tag)
    # the WIDE film travels with the clip: Instagram is given it (poster.instagram, "wide")
    wide = stem + "__wide.mp4"
    shutil.copy(os.path.join(OUT, f"{slug}.mp4"), wide)
    for f in [stem + ".mp4", wide] + covers:
        r = subprocess.run([gh, "release", "upload", tag, f, "--clobber", "-R", REPO], capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(f"UPLOAD FAILED {os.path.basename(f)}: {r.stderr[-200:]}")
        store.used()
    url = media_store.url(REPO, tag, rel)
    code = subprocess.run(["curl", "-sIL", "-o", "/dev/null", "-w", "%{http_code}", url], capture_output=True, text=True).stdout.strip()
    if code != "200":
        raise SystemExit(f"UPLOADED BUT NOT FETCHABLE {rel}: HTTP {code}")
    key = (p.get("cta_keyword") or "WISH").upper()
    json.dump({"slug": slug, "episode": n, "scenes": info.get("scenes"), "entry": {
        "file": rel, "caption": p["caption"].replace("{episode}", f"Episode {n}: {p['title']}."),
        "hook": " ".join(p["hook"]), "bytes": os.path.getsize(stem + ".mp4"), "done": False, "status": {},
        "media_tag": tag, **({"cover": True} if len(covers) == 2 else {}), "look": "movie", "solo": True, "solo_hours": [3, 3], "wide": True,
        "cta_keyword": key, "cta_variant": 0, "cta_kind": "offer",
        "caption_exact": True, "caption_link": OFFERS[key], "movie": slug, "music": info.get("music"),
        # no music in the film = Instagram waits for Kamay until the evening (engine/main.py, IG_HAND):
        # he can post it there himself with one of Instagram's own tracks; if not, it posts by itself
        **({} if info.get("music") else {"ig_hand": True})}},
        open(os.path.join(OUT, f"{slug}_entry.json"), "w"), indent=1)
    print(f"MOVIE UPLOADED {rel} (release {tag}); entering the queue next")
    return 0


def enter(path):
    """The uploaded film goes into the posting queue. Run on main AS IT IS NOW (the poster
    rewrites the manifest every few minutes), so the workflow can simply try again."""
    slug = load(path)["slug"]
    e = json.load(open(os.path.join(OUT, f"{slug}_entry.json")))
    mp = os.path.join(ROOT, "state", "manifest.json")
    man = json.load(open(mp))
    d = done()
    entry = e["entry"]
    old = next((c for c in man["clips"] if c["file"] == entry["file"]), None)
    if old is not None:
        if old.get("posted_at") or old.get("done"):
            print(entry["file"], "has already posted - nothing changed")
            return 0
        for k_ in ("bytes", "music", "caption", "hook", "cover", "media_tag", "solo_hours", "ig_hand", "wide"):
            if k_ in entry:
                old[k_] = entry[k_]
        json.dump(man, open(mp, "w"), indent=1)
        d["built"][slug].update({"music": entry.get("music"), "scenes": e.get("scenes"), "rebuilt": True})
        if d.get("music"):
            d["music"][-1] = entry.get("music")
        json.dump(d, open(DONE, "w"), indent=1)
        print(f"MOVIE REPLACED {entry['file']}: the new film is in the queue, still posting {old.get('scheduled_at')}")
        return 0
    entry["scheduled_at"] = next_slot(man["clips"])
    man["clips"].append(entry)
    json.dump(man, open(mp, "w"), indent=1)
    d["built"][slug] = {"file": entry["file"], "episode": e["episode"], "posts": entry["scheduled_at"],
                        "music": entry.get("music"), "scenes": e.get("scenes")}
    d["music"] = (d.get("music", []) + [entry.get("music")])[-40:]
    d["next_episode"] = max(int(d["next_episode"]), e["episode"] + 1)
    json.dump(d, open(DONE, "w"), indent=1)
    print(f"MOVIE QUEUED {entry['file']}: posts {entry['scheduled_at']} New York, alone (3 h clear before and after)")
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "check":
        rc = 0
        for f in sys.argv[2:]:
            bad = check(f)
            print(("REFUSED " if bad else "OK ") + os.path.basename(f), *bad, sep="\n  ")
            rc |= bool(bad)
        sys.exit(rc)
    if cmd == "pick":
        pick(sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else None)
    elif cmd == "spec":
        spec(sys.argv[2])
    elif cmd == "gate":
        sys.exit(gate(sys.argv[2]))
    elif cmd == "queue":
        sys.exit(queue(sys.argv[2]))
    elif cmd == "enter":
        sys.exit(enter(sys.argv[2]))
    else:
        raise SystemExit(__doc__)
