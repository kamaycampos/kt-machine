#!/usr/bin/env python3
"""READ-ONLY: what the DM bot sees on a brand's Facebook Page. Sends nothing; no names printed."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dm_reply as dm
page, tok = dm.env("FB_PAGE_ID"), dm.env("FB_ACCESS_TOKEN")
kws = dm.keywords()
print("keywords:", kws)
for edge in ("video_reels", "posts", "videos"):
    try:
        items = dm._get(f"{dm.G}/{page}/{edge}", {"fields": "id,created_time,updated_time", "limit": 6, "access_token": tok}).get("data", [])
    except Exception as e:
        print(edge, "ERROR", e); continue
    print(f"{edge}: {len(items)}")
    for v in items:
        try:
            cs = dm._get(f"{dm.G}/{v['id']}/comments", {"fields": "id,message,created_time,from", "limit": 50,
                                                      "filter": "stream", "access_token": tok}).get("data", [])
        except Exception as e:
            print("   ", v["id"][-5:], "comments ERROR", e); continue
        print("   ", v["id"][-5:], (v.get("created_time") or v.get("updated_time") or "")[:16], "comments", len(cs),
              [(c["created_time"][:16], dm.matched(c.get("message", ""), kws), bool(c.get("from"))) for c in cs[:5]])
