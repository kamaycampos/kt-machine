#!/usr/bin/env python3
"""READ-ONLY: what the comment -> DM bot can see. Sends nothing, writes nothing.
Prints no usernames (public repository logs)."""
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dm_reply as dm

P = os.environ.get("DIAG_PREFIX", "")          # "AR_" = Awakened Rise
ig, tok = os.environ[P + "IG_USER_ID"], os.environ.get(P + "FB_ACCESS_TOKEN") or os.environ[P + "IG_ACCESS_TOKEN"]
if P:
    os.environ["KT_CTA_KEYWORDS"] = os.environ.get(P + "CTA_KEYWORDS", "")
kws, d, now = dm.keywords(), dm.load(), datetime.now(timezone.utc)
print("keywords:", kws)
for name in ("FB_ACCESS_TOKEN", "IG_ACCESS_TOKEN"):
    t = os.environ.get(P + name, "")
    if t:
        try:
            dt = dm._get(f"{dm.G}/debug_token", {"input_token": t, "access_token": t}).get("data", {})
            print(f"{P}{name}: type {dt.get('type')} valid {dt.get('is_valid')} expires {dt.get('expires_at')}"
                  f" profile {dt.get('profile_id')} scopes {sorted(dt.get('scopes', []))}")
        except Exception as e:
            print(f"{P}{name}: debug_token failed - {e}")
print("page id matches:", os.environ.get(P + "FB_PAGE_ID", "")[-4:])
url, params, posts = f"{dm.G}/{ig}/media", {"fields": "id,timestamp,comments_count,media_product_type",
                                             "limit": 50, "access_token": tok}, []
while url and len(posts) < 150:
    j = dm._get(url, params)
    posts += j.get("data", [])
    url, params = (j.get("paging") or {}).get("next"), {}
print(f"posts read: {len(posts)}, newest {posts[0]['timestamp'][:16]}, oldest {posts[-1]['timestamp'][:16]}")
for i, m in enumerate(posts):
    if not m.get("comments_count"):
        continue
    cs = dm._get(f"{dm.G}/{m['id']}/comments", {"fields": "id,text,timestamp,replies{username}",
                                                 "limit": 50, "access_token": tok}).get("data", [])
    print(f"#{i:3d} post {m['timestamp'][:16]} {m.get('media_product_type','')}: count {m['comments_count']}, API gave {len(cs)}")
    for c in cs:
        age = (now - dm._ts(c["timestamp"])).days
        kw = dm.matched(c.get("text", ""), kws)
        st = "SENT" if c["id"] in d["sent"] else "seen" if c["id"] in d["seen"] else "new"
        rep = len((c.get("replies") or {}).get("data", []))
        print(f"      {age:2d}d kw={kw or '-':6s} {st:4s} replies={rep} text={json.dumps((c.get('text') or '')[:25])}")
