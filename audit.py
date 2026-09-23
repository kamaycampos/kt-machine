"""Is the whole machine actually working? One screen, no guessing.

23 Sept 2026. Three bugs in one night shared a shape: the work happened and the
record of it was lost, and each was found only because someone went looking.
This looks in every place at once - the queue, the posting cadence, the last run
of every workflow, the month's episode list, the planner's output and the
measurements - and prints what is wrong in plain words.

    python audit.py            # from anywhere in the repo
"""
import datetime as dt
import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = "kamaycampos/kt-machine"
GH = os.path.expanduser("~/Kamay/bin/gh")
now = dt.datetime.utcnow()
# The machine writes posted_at and scheduled_at in Kamay's own clock (New York),
# while workflow timestamps are UTC. Comparing the two was the first thing this
# script got wrong about itself.
local = now - dt.timedelta(hours=4)
bad = []


def gh(*a):
    r = subprocess.run([GH, *a], capture_output=True, text=True)
    return r.stdout.strip()


def load(p):
    try:
        return json.load(open(os.path.join(HERE, p)))
    except Exception:
        return None


print(f"== KT MACHINE, {now:%d %b %H:%M} UTC ==\n")

# 1. THE QUEUE
man = (load("state/manifest.json") or {}).get("clips", [])
ours = [c for c in man if not c["file"].startswith("AR_")]
queue = [c for c in ours if not c.get("done") and not c.get("posted_at")]
last = max((c["scheduled_at"][:10] for c in queue if c.get("scheduled_at")), default=None)
days = len(queue) / 6
print(f"QUEUE       {len(queue)} clips, about {days:.1f} days at 6/day"
      + (f", last scheduled {last}" if last else ""))
if days < 3:
    bad.append(f"queue is down to {days:.1f} days - the planner needs to run")

# 2. POSTING
posted = sorted([c for c in ours if c.get("posted_at")], key=lambda c: c["posted_at"])
today = [c for c in posted if c["posted_at"][:10] == f"{local:%Y-%m-%d}"]
since = (local - dt.datetime.fromisoformat(posted[-1]["posted_at"][:16])).total_seconds() / 3600 if posted else 99
print(f"POSTING     {len(today)} today, {len(posted)} all time, last one {since:.1f}h ago")
if since > 8:
    bad.append(f"nothing has posted for {since:.0f} hours")
retry = [c["file"] for c in ours if c.get("tiktok_retry")]
if retry:
    print(f"TIKTOK      retry pending: {', '.join(retry)}")

# 3. EVERY WORKFLOW'S LAST RUN
print("\nWORKFLOWS   (last run of each)")
runs = json.loads(gh("run", "list", "-R", REPO, "-L", "40", "--json",
                     "workflowName,status,conclusion,createdAt") or "[]")
seen = {}
for r in runs:
    seen.setdefault(r["workflowName"], r)
for name, r in seen.items():
    if name.startswith("pages"):
        continue
    age = (now - dt.datetime.fromisoformat(r["createdAt"][:16])).total_seconds() / 3600
    state = r["conclusion"] or r["status"]
    flag = "" if state in ("success", "in_progress", "queued", "pending") else "  <-- FAILED"
    print(f"  {name:14} {state:11} {age:5.1f}h ago{flag}")
    if flag:
        bad.append(f"{name} last run {state}")

# 4. THE MONTH'S EPISODES AND THE PLANS
plans = [f[:-5] for f in os.listdir(os.path.join(HERE, "factory", "plans"))
         if f.endswith(".json") and not f.startswith("_")]
done = load("factory/plans/_done.json") or []
order = [e["id"] for e in (load("factory/source_plan.json") or {}).get("episodes", [])]
txt = " ".join(open(os.path.join(HERE, "factory", "plans", f)).read()
               for f in os.listdir(os.path.join(HERE, "factory", "plans")) if f.endswith(".json"))
unplanned = [v for v in order if f'"{v}.mp4"' not in txt]
print(f"\nPLANS       {len(plans)} written, {len(done)} built; month list has {len(unplanned)} episodes left to plan")
if len(unplanned) < 4:
    bad.append("the month's episode list is nearly used up - extend source_plan.json")
waiting = [p for p in plans if p not in done]
if waiting:
    print(f"            waiting to build: {', '.join(waiting)}")

# 5. MEASUREMENT
rows = load("state/metrics.json") or []
tt = load("state/tiktok.json") or {}
fresh = max((r["at"] for r in rows), default="")
print(f"\nMEASURED    {len(rows)} samples, newest {fresh or 'never'}; "
      f"TikTok {tt.get('at', 'never')} ({(tt.get('profile') or {}).get('follower_count', '?')} followers)")
if fresh and (now - dt.datetime.fromisoformat(fresh[:16])).days >= 1:
    bad.append("measurement has not run in over a day")
hooked = sum(1 for c in ours if c.get("hook"))
print(f"            {hooked} of {len(ours)} clips carry their on-screen hook")

print("\n" + ("ALL GOOD - nothing needs a human." if not bad else "NEEDS ATTENTION:"))
for b in bad:
    print(f"  - {b}")
