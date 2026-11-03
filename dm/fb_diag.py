#!/usr/bin/env python3
"""READ-ONLY: every Facebook reel of a brand with its views, to find when they went invisible."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dm_reply as dm
page, tok = dm.env("FB_PAGE_ID"), dm.env("FB_ACCESS_TOKEN")
url, params, rows = f"{dm.G}/{page}/video_reels", {"fields": "id,created_time,post_views,length", "limit": 100, "access_token": tok}, []
while url and len(rows) < 600:
    j = dm._get(url, params); rows += j.get("data", []); url, params = (j.get("paging") or {}).get("next"), {}
print("reels:", len(rows))
for r in rows:
    print("R", r["created_time"][:16], r["id"][-5:], "views", r.get("post_views"))
