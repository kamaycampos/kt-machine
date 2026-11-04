"""READ-ONLY (4 Nov 2026): every comment the AR key can see on her newest Instagram posts,
and what the DM bot's state says about each. Sends nothing. Prints no usernames (public logs)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
os.environ["DM_BRAND"] = "AR_"
import dm_reply as m
d = json.load(open(m.STATE))
kws = m.keywords()
ig, tok = m.env("IG_USER_ID"), m.env("FB_ACCESS_TOKEN")
me = {m.env("FB_PAGE_ID"), ig, m._get(f"{m.G}/{ig}", {"fields": "username", "access_token": tok}).get("username", "")}
media = m._get(f"{m.G}/{ig}/media", {"fields": "id,timestamp,comments_count,caption", "limit": 12,
                                     "access_token": tok}).get("data", [])
for p in media:
    cs = m._get(f"{m.G}/{p['id']}/comments", {"fields": "id,text,timestamp,username,replies{username}",
                                              "limit": 50, "access_token": tok}).get("data", [])
    print(f"post {p['timestamp'][:16]} ...{p['id'][-5:]} says {p.get('comments_count')} comments, API gave {len(cs)}"
          f" | {(p.get('caption') or '')[:40]!r}")
    for c in cs:
        reps = {r.get('username', '') for r in (c.get('replies') or {}).get('data', [])}
        cid = c["id"]
        st = "SENT" if cid in d["sent"] else ("seen " + d["seen"][cid][:16] if cid in d["seen"] else "NEW")
        print(f"   {c['timestamp'][:16]} ...{cid[-5:]} {(c.get('text') or '')[:20]!r} kw={m.matched(c.get('text'), kws)}"
              f" by_me={c.get('username') in me} replied_by_me={bool(reps & me)} replies={len(reps)} -> {st}")

# 4 Nov 2026: a real "RISE" came back with EMPTY text in the list. Ask for each blank one directly.
for p in media:
    for c in m._get(f"{m.G}/{p['id']}/comments", {"fields": "id,text", "limit": 50, "access_token": tok}).get("data", []):
        if (c.get("text") or "").strip():
            continue
        for f in ("text", "hidden", "like_count", "media{id}", "parent_id", "from{id}", "user"):
            try:
                r = m._get(f"{m.G}/{c['id']}", {"fields": f, "access_token": tok})
                r.pop("id", None)
                if f == "from{id}" or f == "user":
                    r = {k: "present" for k in r}
                print(f"   blank ...{c['id'][-5:]} {f}: {r}")
            except Exception as e:
                print(f"   blank ...{c['id'][-5:]} {f}: ERR {e}")
