"""READ-ONLY (4 Nov 2026): the thread around the one comment the AR bot answered today.
No usernames printed: the same person is shown as SAME."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
os.environ["DM_BRAND"] = "AR_"
import dm_reply as m
tok = m.env("FB_ACCESS_TOKEN")
cid, post = "18111593861614618", "17923212057460786"
p = m._get(f"{m.G}/{post}", {"fields": "timestamp,caption,permalink,comments_count", "access_token": tok})
print(f"POST {p.get('timestamp')} {p.get('permalink')} comments_count={p.get('comments_count')}")
print(f"   caption: {(p.get('caption') or '')[:90]!r}")
who = (m._get(f"{m.G}/{cid}", {"fields": "from{id}", "access_token": tok}).get("from") or {}).get("id")
for c in m._get(f"{m.G}/{post}/comments", {"fields": "id,text,timestamp,like_count,from{id},replies{id,text,timestamp,from{id}}",
                                          "limit": 50, "access_token": tok}).get("data", []):
    tag = "SAME" if (c.get("from") or {}).get("id") == who else "other"
    print(f" {c['timestamp'][:16]} ...{c['id'][-5:]} [{tag}] likes={c.get('like_count')} text={(c.get('text'))!r}")
    for r in (c.get("replies") or {}).get("data", []):
        rid = (r.get("from") or {}).get("id")
        t = "SAME" if rid == who else ("US" if rid == m.env("IG_USER_ID") else "other")
        print(f"     reply {r['timestamp'][:16]} [{t}] text={(r.get('text'))!r}")
