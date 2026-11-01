#!/usr/bin/env python3
"""Instagram TRIAL REELS, every day, by themselves (1 Nov 2026).

Kamay: "the test of posting 7 clips a day in IG never got delivered by you." trial.py could
post an experiment by hand since 3 Sept; nothing ever made one. Now the planner gives ONE
strong clip a day up to 7 alternative hooks ("trial_hooks"), the factory renders them
(build_shard.py: same footage, same captions, ONLY the hook card differs) and lists them in
state/variants.json, and this runs after every posting pass (run_once.py):

  POST   the first experiment whose clip has itself posted: every arm as a Trial Reel
         (non-followers only, never on the grid). Stops on the first one that is not a
         trial, exactly like trial.py - an experiment lost costs a render; seven near-
         identical reels to followers cannot be undone. One experiment per run.
  SCORE  48 h later: views and reach of every arm from Instagram; the winning hook is
         written down, so the planner and the strategist learn which WORDS this audience
         stops for. Graduating the winner to followers stays a tap in the app.
"""
import datetime as dt
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
VP = os.path.join(HERE, "state", "variants.json")
G = "https://graph.facebook.com/v21.0"


def _load():
    try:
        return json.load(open(VP))
    except (OSError, ValueError):
        return {}


def step(engine, poster, media_url, log=print):
    var = _load()
    if not var:
        return
    now = dt.datetime.utcnow()
    man = engine.load()
    changed = False
    for key, e in var.items():
        if e.get("posted"):
            continue
        clip = next((c for c in man["clips"] if c["file"] == e["clip"]), None)
        if not clip or not clip.get("posted_at"):
            continue
        log(f"TRIAL {key}: posting {len(e['arms'])} hook variant(s) as Trial Reels")
        for arm in e["arms"]:
            path = os.path.join(engine.MEDIA, arm["rel"])
            try:
                if not os.path.exists(path):
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    urllib.request.urlretrieve(media_url(arm["rel"]), path)
                poster.LAST_MEDIA_ID = None
                res = poster.instagram(path, clip.get("caption", ""), media_url(arm["rel"]), clip, trial=True)
            except Exception as x:                       # one arm failing never stops posting
                res = f"error: {type(x).__name__}: {x}"
            ok = isinstance(res, tuple)
            arm["status"] = str(res[0] if ok else res)[:160]
            arm["id"] = poster.LAST_MEDIA_ID if ok else None
            log(f"  {' / '.join(arm['hook'])}: {arm['status']}")
            if not ok or arm["status"].startswith("PUBLISHED BUT NOT A TRIAL"):
                log("  STOPPED: that one did not publish as a trial; the rest were NOT posted.")
                break
        e["posted"] = now.strftime("%Y-%m-%dT%H:%M")
        changed = True
        break
    tok = os.environ.get("IG_ACCESS_TOKEN", "")
    for key, e in var.items():
        if not e.get("posted") or e.get("scored") or not tok:
            continue
        if now - dt.datetime.fromisoformat(e["posted"]) < dt.timedelta(hours=48):
            continue
        for arm in e["arms"]:
            if not arm.get("id"):
                continue
            try:
                d = json.load(urllib.request.urlopen(
                    f"{G}/{arm['id']}/insights?metric=views,reach&access_token={tok}", timeout=30))
                for m in d.get("data", []):
                    arm[m["name"]] = (m.get("values") or [{}])[0].get("value")
            except Exception as x:
                arm["insights_error"] = str(x)[:120]
        scored = [a for a in e["arms"] if isinstance(a.get("views"), int)]
        if scored:
            best = max(scored, key=lambda a: a["views"])
            e["winner"] = {"hook": best["hook"], "views": best["views"],
                           "others": sorted((a["views"] for a in scored if a is not best), reverse=True)}
            log(f"TRIAL {key}: winner '{' / '.join(best['hook'])}' {best['views']} views")
        e["scored"] = now.strftime("%Y-%m-%dT%H:%M")
        changed = True
    if changed:
        json.dump(var, open(VP, "w"), indent=1, ensure_ascii=False)
