#!/usr/bin/env python3
"""READ-ONLY: which app published a reel, and its post's visibility. Sends nothing; no names of people."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dm_reply as dm
page, tok = dm.env("FB_PAGE_ID"), dm.env("FB_ACCESS_TOKEN")
for vid in sys.argv[1:]:
    for f in ("post_id", "application", "from", "published", "privacy", "is_reference_only"):
        try:
            j = dm._get(f"{dm.G}/{vid}", {"fields": f, "access_token": tok}); j.pop("id", None)
            print(vid[-5:], f, str(j)[:200])
        except Exception as e:
            print(vid[-5:], f, "ERR", str(e)[:140])
    try:
        pid = dm._get(f"{dm.G}/{vid}", {"fields": "post_id", "access_token": tok}).get("post_id")
        if pid:
            full = pid if "_" in pid else f"{page}_{pid}"
            j = dm._get(f"{dm.G}/{full}", {"fields": "application,is_published,is_hidden,privacy,status_type,permalink_url",
                                           "access_token": tok}); j.pop("id", None)
            print(vid[-5:], "POST", str(j)[:300])
    except Exception as e:
        print(vid[-5:], "POST ERR", str(e)[:160])
    for metric in ("blue_reels_play_count", "fb_reels_total_plays", "post_video_views"):
        try:
            j = dm._get(f"{dm.G}/{vid}/video_insights", {"metric": metric, "access_token": tok}).get("data", [])
            print(vid[-5:], "PLAYS", metric, [v.get("value") for x in j for v in x.get("values", [])][:3])
        except Exception as e:
            print(vid[-5:], "PLAYS", metric, "ERR", str(e)[:100])
