#!/usr/bin/env python3
"""READ-ONLY (16 Nov 2026): the bot recorded a public reply under every Instagram comment it
messaged - is each reply still there? Reads every Instagram send on record back from Instagram:
the comment, the replies under it, and the reply the bot wrote. A person is shown only as the
first letter and length of the username. Sends nothing."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DM_BRAND", "AR_")
import dm_reply as m

ig, tok = m.env("IG_USER_ID"), m.env("FB_ACCESS_TOKEN")
d = json.load(open(m.STATE))
mine = m._get(f"{m.G}/{ig}", {"fields": "username", "access_token": tok}).get("username", "")
there = gone = 0
for cid, r in sorted(d["sent"].items(), key=lambda x: x[1]["sent_at"]):
    if r.get("platform") != "instagram":
        continue
    line = f"sent {r['sent_at'][:16]} {r['keyword']:5} recorded public_reply={r.get('public_reply')!r}"
    try:
        c = m._get(f"{m.G}/{cid}", {"fields": "id,hidden,username,timestamp,replies{id,username,timestamp,hidden,text}",
                                    "access_token": tok})
        u = c.get("username") or ""
        reps = (c.get("replies") or {}).get("data", [])
        ours = [x for x in reps if x.get("username") == mine]
        there += bool(ours); gone += not ours
        print(f"{line} | comment readable, by {u[:1]}..({len(u)}), hidden={c.get('hidden')}, replies under it: {len(reps)},"
              f" OURS: {len(ours)} {[(x['timestamp'][:16], 'hidden=' + str(x.get('hidden'))) for x in ours]}")
    except Exception as e:
        gone += 1
        print(f"{line} | comment NOT readable: {str(e)[:110]}")
    try:
        p = m._get(f"{m.G}/{r['post']}", {"fields": "permalink,comments_count,timestamp", "access_token": tok})
        n = m._get(f"{m.G}/{r['post']}/comments", {"fields": "id", "limit": 50, "access_token": tok}).get("data", [])
        print(f"      reel {p.get('timestamp', '')[:16]} {p.get('permalink')} counts {p.get('comments_count')}, list gives {len(n)},"
              f" this comment in the list: {any(x['id'] == cid for x in n)}")
    except Exception as e:
        print(f"      reel ERR {str(e)[:110]}")
print(f"our public reply still under the comment: {there} | missing: {gone}")
