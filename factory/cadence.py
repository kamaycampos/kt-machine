"""THE CADENCE RULE - Kamay, 17 Oct 2026. Runs every 2 hours (cadence.yml).

    "unless 4-6 posts has been posted for any reason, the engine works non-stop until
    its done ... every 2 hours until we hit the 4-6 posts a day. outside of this
    situation, we should have the engine smartly working ... all already scheduled in."

So there are two modes, and this script decides which one the day is in:
- ON TRACK: today's posts (done + still booked for later today) >= CADENCE_MIN. Nothing
  happens; the scheduler's slot grid carries the day.
- SHORT: fewer than CADENCE_MIN. Every 2 hours the machine does the next production
  step until the day is covered:
    1. plans written but never built -> start the factory (it builds them);
    2. under two days of clips waiting -> wake the cloud planner (a GitHub
       repository_dispatch, which a claude.ai webhook trigger turns into a planner run),
       at most once every PLAN_COOLDOWN_H hours, so a planner with nothing to plan is not
       woken twelve times a day.
It never touches state/manifest.json (the post workflow owns it; two writers collided
on 11 Oct). It prints its decision as KEY=VALUE lines for the workflow to act on.

    python factory/cadence.py            # decide (reads state + plans)
"""
import datetime as dt
import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MIN = int(os.environ.get("CADENCE_MIN") or 4)
TWO_DAYS = int(os.environ.get("CADENCE_STOCK") or 12)
COOLDOWN_H = float(os.environ.get("PLAN_COOLDOWN_H") or 4)
TAG = "cadence-plan-fired"


def now_local():
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo(os.environ.get("KT_TZ") or "America/New_York")).replace(tzinfo=None)
    except Exception:
        return dt.datetime.utcnow() - dt.timedelta(hours=4)


def mine(c):
    # The fence: AR_ clips are another person's account and never count here.
    return not str(c.get("file", "")).startswith("AR_")


def last_plan_fire():
    """When this rule last woke the planner (an annotated tag carries the time)."""
    try:
        subprocess.run(["git", "fetch", "-q", "-f", "origin", f"refs/tags/{TAG}:refs/tags/{TAG}"],
                       cwd=ROOT, capture_output=True, timeout=60)
        out = subprocess.run(["git", "for-each-ref", "--format=%(taggerdate:iso-strict)", f"refs/tags/{TAG}"],
                             cwd=ROOT, capture_output=True, text=True).stdout.strip()
        return dt.datetime.fromisoformat(out).astimezone(dt.timezone.utc).replace(tzinfo=None) if out else None
    except Exception:
        return None


def main():
    clips = [c for c in json.load(open(os.path.join(ROOT, "state", "manifest.json")))["clips"] if mine(c)]
    now = now_local()
    today, hhmm = now.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%dT%H:%M")
    posted = [c for c in clips if str(c.get("posted_at") or "").startswith(today)]
    waiting = [c for c in clips if not c.get("done") and not c.get("posted_at")]
    booked = [c for c in waiting if str(c.get("scheduled_at") or "").startswith(today)
              and str(c.get("scheduled_at")) >= hhmm]
    have = len(posted) + len(booked)

    plans_dir = os.path.join(HERE, "plans")
    try:
        done = set(json.load(open(os.path.join(plans_dir, "_done.json"))))
    except Exception:
        done = set()
    unbuilt = sorted(f[:-5] for f in os.listdir(plans_dir)
                     if f.startswith("ep_") and f.endswith(".json") and f[:-5] not in done)

    print(f"# {today} {now:%H:%M} local: posted {len(posted)}, booked later today {len(booked)}, "
          f"waiting {len(waiting)}, unbuilt plans {len(unbuilt)}")
    if have >= MIN:
        print(f"# ON TRACK ({have} >= {MIN}): the slot grid carries the day")
        print("short=no\nbuild=no\nplan=no")
        return
    print(f"# SHORT ({have} < {MIN}): production steps")
    print("short=yes")
    print("build=" + ("yes" if unbuilt else "no"))
    want_plan = len(waiting) < TWO_DAYS
    last = last_plan_fire()
    if want_plan and last and (dt.datetime.utcnow() - last).total_seconds() < COOLDOWN_H * 3600:
        print(f"# planner woken {last:%H:%M} UTC, inside the {COOLDOWN_H:g}h cooldown - not again yet")
        want_plan = False
    print("plan=" + ("yes" if want_plan else "no"))


if __name__ == "__main__":
    main()
