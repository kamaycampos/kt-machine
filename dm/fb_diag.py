#!/usr/bin/env python3
"""READ-ONLY: are a brand's Facebook reels actually published? Sends nothing; no names printed."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dm_reply as dm
page, tok = dm.env("FB_PAGE_ID"), dm.env("FB_ACCESS_TOKEN")
items = dm._get(f"{dm.G}/{page}/video_reels", {"fields": "id", "limit": 40, "access_token": tok}).get("data", [])
print("reels listed:", len(items))
for v in items:
    try:
        j = dm._get(f"{dm.G}/{v['id']}", {"fields": "created_time,published,status,permalink_url,is_instagram_eligible,privacy",
                                          "access_token": tok})
    except Exception as e:
        print("  ", v["id"][-5:], "ERROR", e); continue
    st = j.get("status") or {}
    print("  ", v["id"][-5:], (j.get("created_time") or "")[:16], "published", j.get("published"),
          "video", st.get("video_status"), "| publish", (st.get("publishing_phase") or {}).get("status"),
          "| upload", (st.get("uploading_phase") or {}).get("status"),
          "| processing", (st.get("processing_phase") or {}).get("status"),
          "| privacy", (j.get("privacy") or {}).get("value"), "|", "permalink" if j.get("permalink_url") else "no link")
