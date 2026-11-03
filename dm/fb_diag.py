#!/usr/bin/env python3
"""READ-ONLY: links of a brand's newest Facebook reels. Sends nothing; no names printed."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dm_reply as dm
page, tok = dm.env("FB_PAGE_ID"), dm.env("FB_ACCESS_TOKEN")
for v in dm._get(f"{dm.G}/{page}/video_reels", {"fields": "id,permalink_url,created_time", "limit": 3, "access_token": tok}).get("data", []):
    print("REEL", v["created_time"][:16], "https://www.facebook.com" + v.get("permalink_url", "") if v.get("permalink_url", "").startswith("/") else v.get("permalink_url"), v["id"])
