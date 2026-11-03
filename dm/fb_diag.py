#!/usr/bin/env python3
"""READ-ONLY: why a brand's Facebook reels can't be seen - copyright/blocks. Sends nothing; no names."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dm_reply as dm
page, tok = dm.env("FB_PAGE_ID"), dm.env("FB_ACCESS_TOKEN")
reels = dm._get(f"{dm.G}/{page}/video_reels", {"fields": "id,created_time", "limit": 60, "access_token": tok}).get("data", [])
print("reels:", len(reels), "oldest listed", reels[-1]["created_time"][:10] if reels else "-")
for v in reels[:4] + reels[-3:]:
    for f in ("copyright_check_information", "copyright_monitoring_status", "is_crossposting_eligible",
              "is_instagram_eligible", "post_views", "views", "video_insights.metric(total_video_views)"):
        try:
            j = dm._get(f"{dm.G}/{v['id']}", {"fields": f, "access_token": tok})
            j.pop("id", None)
            print("  ", v["created_time"][:10], v["id"][-5:], str(j)[:220])
        except Exception as e:
            print("  ", v["created_time"][:10], v["id"][-5:], f, "ERR", str(e)[:120])
