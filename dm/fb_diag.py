#!/usr/bin/env python3
"""READ-ONLY: one Facebook reel's comments as the DM bot sees them. Sends nothing; no names printed."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dm_reply as dm
tok, kws = dm.env("FB_ACCESS_TOKEN"), dm.keywords()
for vid in sys.argv[1:]:
    try:
        j = dm._get(f"{dm.G}/{vid}", {"fields": "created_time,from,comments.summary(true).limit(0),likes.summary(true).limit(0)",
                                      "access_token": tok})
        print(vid, (j.get("created_time") or "")[:16], "owner end", (j.get("from") or {}).get("id", "")[-4:],
              "comments total", (j.get("comments") or {}).get("summary", {}).get("total_count"),
              "likes", (j.get("likes") or {}).get("summary", {}).get("total_count"))
        for f in ("stream", "toplevel"):
            cs = dm._get(f"{dm.G}/{vid}/comments", {"fields": "id,message,created_time", "limit": 25, "filter": f,
                                                  "order": "reverse_chronological", "access_token": tok}).get("data", [])
            print("  ", f, len(cs), [(c["created_time"][:16], dm.matched(c.get("message", ""), kws)) for c in cs[:8]])
    except Exception as e:
        print(vid, "ERROR", e)
