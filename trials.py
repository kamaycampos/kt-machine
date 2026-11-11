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


TRIES = 3          # runs an arm may fail in before it is given up
# ONE ARM PER RUN (9 Nov 2026). Posting all 7 arms in one burst got 23 of 91 refused
# "User is performing too many actions" (code 9) and 26 with a transient 500: Instagram
# reads 7 reels in a minute as a bot. The post job runs every ~20 min, so one arm a run
# spreads an experiment over 2-3 hours like a person. A refusal that is Instagram's
# throttle or its own transient error is not the arm's fault: it waits, it costs no try.
ARMS_PER_RUN = 1
WAITS = 40         # throttled runs an arm may sit out before it is given up


def _throttled(status):
    s = str(status)
    return "too many actions" in s or "'is_transient': True" in s or "is_transient\": true" in s
RESERVE = 25       # API posts a day kept free for the real clips and their stories


def _room(poster, clip):
    """Posts this brand's Instagram can still take today, or None when unknown.

    Meta caps API-published posts per account per 24 h (content_publishing_limit).
    Seven trials per clip on every clip reaches it on a busy day, and the real clips
    must never be the ones refused."""
    try:
        (ig, tok), missing = poster._cfg("IG_USER_ID", "IG_ACCESS_TOKEN", brand=poster.brand_of(clip))
        if missing:
            return None
        d = json.load(urllib.request.urlopen(
            f"{G}/{ig}/content_publishing_limit?fields=quota_usage,config&access_token={tok}", timeout=30))
        row = (d.get("data") or [{}])[0]
        return int((row.get("config") or {}).get("quota_total", 50)) - int(row.get("quota_usage", 0)) - RESERVE
    except Exception:
        return None


# A BLOCK PAUSES EVERY TRIAL FOR 72 HOURS (10 Nov 2026). "User is performing too many actions"
# (code 9, is_transient False) is Instagram's action block on the ACCOUNT. The 9 Nov fix made a
# blocked arm wait one run (~20 min) and try again: 26 refusals in a row, each one another flagged
# action against the account whose real reels were losing reach (KT IG median 207-979 -> 67-189
# since trials began ~1 Nov). One block now stops trials for that account for 72 h; the real
# clips keep posting.
PAUSE = os.path.join(HERE, "state", "trials_pause.json")
PAUSE_H = 72
FOLLOW_D = 7
LAST = os.path.join(HERE, "state", "trials_last.json")
GAP_H = 2


def _paused(now):
    try:
        until = json.load(open(PAUSE)).get("until", "")
    except (OSError, ValueError):
        return ""
    return until if until and now.strftime("%Y-%m-%dT%H:%M") < until else ""


def step(engine, poster, media_url, log=print):
    var = _load()
    if not var:
        return
    now = dt.datetime.utcnow()
    held = _paused(now)
    if held:
        try:
            why = json.load(open(PAUSE)).get("why", "")[:120]
        except (OSError, ValueError):
            why = ""
        log(f"TRIALS PAUSED until {held} UTC - {why or 'Instagram action block'}; real clips unaffected")

    man = engine.load()
    changed = False
    for key, e in var.items():
        if held:
            break                                   # nothing posts while paused; scoring below still runs
        if e.get("posted"):
            continue
        clip = next((c for c in man["clips"] if c["file"] == e["clip"]), None)
        if not clip or not clip.get("posted_at"):
            continue
        todo = [a for a in e["arms"] if not a.get("id") and a.get("tries", 0) < TRIES]
        room = _room(poster, clip)
        if room is not None and room < len(todo):
            log(f"TRIAL {key}: waiting - Instagram can take {max(room, 0)} more API post(s) today "
                f"after the {RESERVE} kept for real clips")
            break
        # ONE TRIAL EVERY 2 HOURS (11 Nov 2026). One arm per ~20-min run was still 3 reels an hour on
        # top of the real clips, and Instagram answered with an action block. Spaced like a person.
        try:
            last = json.load(open(LAST)).get("at", "")
        except (OSError, ValueError):
            last = ""
        if last and now - dt.datetime.fromisoformat(last) < dt.timedelta(hours=GAP_H):
            log(f"TRIAL {key}: next trial after {(dt.datetime.fromisoformat(last) + dt.timedelta(hours=GAP_H)):%H:%M} UTC (one every {GAP_H}h)")
            break
        log(f"TRIAL {key}: posting {min(len(todo), ARMS_PER_RUN)} of {len(todo)} hook variant(s) left as Trial Reels")
        for arm in todo[:ARMS_PER_RUN]:
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
            if ok:
                json.dump({"at": now.strftime("%Y-%m-%dT%H:%M")}, open(LAST, "w"))
            arm["status"] = str(res[0] if ok else res)[:160]
            arm["id"] = poster.LAST_MEDIA_ID if ok else None
            if not ok and "too many actions" in str(res):
                until = (now + dt.timedelta(hours=PAUSE_H)).strftime("%Y-%m-%dT%H:%M")
                json.dump({"until": until, "why": str(res)[:160]}, open(PAUSE, "w"), indent=1)
                arm["status"] = "waiting - Instagram action block, trials paused 72h"
                log(f"  {' / '.join(arm['hook'])}: Instagram action block - ALL trials paused until {until} UTC")
                changed = True
                break
            # TOO FEW FOLLOWERS (11 Nov 2026). Code 10 subcode 2207081 is Instagram's minimum-
            # followers rule for trial reels - not a missing app permission, nothing to grant. WB
            # (22 followers) got it 70 times. Pause a week, then one try tells if the account
            # crossed the line; it resumes by itself the day it does.
            if not ok and ("2207081" in str(res) or "does not have permission" in str(res)):
                until = (now + dt.timedelta(days=FOLLOW_D)).strftime("%Y-%m-%dT%H:%M")
                json.dump({"until": until, "why": "too few followers for Instagram trial reels "
                           "(code 10/2207081) - rechecks by itself weekly"}, open(PAUSE, "w"), indent=1)
                arm["status"] = "waiting - account below Instagram's trial-reel follower minimum"
                log(f"  trials need more followers - paused until {until} UTC, then one recheck")
                changed = True
                break
            if not ok and _throttled(res) and arm.get("waits", 0) < WAITS:
                arm["waits"] = arm.get("waits", 0) + 1
                log(f"  {' / '.join(arm['hook'])}: Instagram throttled - waiting for the next run")
                changed = True
                break
            if not ok:
                arm["tries"] = arm.get("tries", 0) + 1
            log(f"  {' / '.join(arm['hook'])}: {arm['status']}")
            # ONLY A NON-TRIAL STOPS THE REST (3 Nov 2026). The first experiment (2 Nov,
            # HE-OWED-37-MILLION) died on arm 1: Instagram answered 500 "is_transient", the
            # loop stopped as if a reel had gone to his followers, and the experiment was
            # marked posted - 0 of 7 trials ever ran. A refused post put nothing anywhere;
            # it is tried again next run (TRIES). Only a reel that published as an ordinary
            # reel stops everything, because that one cannot be undone.
            if ok and arm["status"].startswith("PUBLISHED BUT NOT A TRIAL"):
                e["stopped"] = arm["status"]
                log("  STOPPED: that one did not publish as a trial; the rest were NOT posted.")
                break
        if e.get("stopped") or all(a.get("id") or a.get("tries", 0) >= TRIES for a in e["arms"]):
            e["posted"] = now.strftime("%Y-%m-%dT%H:%M")
        changed = True
        break
    for key, e in var.items():
        # each brand's reels are read with that brand's token (Yaren's live on her account)
        (tok,), _miss = poster._cfg("IG_ACCESS_TOKEN", brand=poster.brand_of({"file": e["clip"]}))
        if not e.get("posted") or e.get("scored") or not tok:
            continue
        if now - dt.datetime.fromisoformat(e["posted"]) < dt.timedelta(hours=48):
            continue
        for arm in e["arms"]:
            if not arm.get("id"):
                continue
            try:
                d = json.load(urllib.request.urlopen(
                    f"{G}/{arm['id']}/insights?metric=views,reach,shares,saved&access_token={tok}", timeout=30))
                for m in d.get("data", []):
                    arm[m["name"]] = (m.get("values") or [{}])[0].get("value")
            except Exception as x:
                arm["insights_error"] = str(x)[:120]
        scored = [a for a in e["arms"] if isinstance(a.get("views"), int)]
        if scored:
            # THE HOOK PEOPLE SEND WINS (3 Nov 2026, VIRALITY.md): sends per reach is Instagram's
            # strongest signal with strangers - and trial reels only ever reach strangers. Views
            # break a tie (and decide when nobody shared).
            def score(a):
                return ((a.get("shares") or 0) / max(1, a.get("reach") or 0), a["views"])
            best = max(scored, key=score)
            e["winner"] = {"hook": best["hook"], "views": best["views"], "shares": best.get("shares"),
                           "reach": best.get("reach"),
                           "others": sorted(((a.get("shares") or 0, a["views"]) for a in scored if a is not best),
                                            reverse=True)}
            log(f"TRIAL {key}: winner '{' / '.join(best['hook'])}' {best.get('shares') or 0} sends, "
                f"{best['views']} views")
        e["scored"] = now.strftime("%Y-%m-%dT%H:%M")
        changed = True
    if changed:
        json.dump(var, open(VP, "w"), indent=1, ensure_ascii=False)
