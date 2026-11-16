#!/usr/bin/env python3
"""READ-ONLY (16 Nov 2026): one reel shows 5 'Rise' comments in Business Suite and the comment
list hands the bot none. Does ANY way of asking return them? Tries the same reel through every
route and prints counts only (a person = first letter + length of the username). Sends nothing."""
import os, sys, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DM_BRAND", "AR_")
import dm_reply as m
tok, tok2, ig = m.env("FB_ACCESS_TOKEN"), m.env("IG_ACCESS_TOKEN"), m.env("IG_USER_ID")
print("same key for both names:", tok == tok2)
def show(label, url, params):
    try:
        r = requests.get(url, params=params, timeout=30); j = r.json()
        if "error" in j:
            print(f"  {label}: ERR {j['error'].get('message', '')[:110]}"); return
        data = j.get("data")
        if data is None:
            data = (j.get("comments") or {}).get("data", [])
        print(f"  {label}: {len(data)} -> {[(c.get('username') or '?')[:1] + str(len(c.get('username') or '')) for c in data]}"
              + (f" count={j.get('comments_count')}" if 'comments_count' in j else ""))
    except Exception as e:
        print(f"  {label}: EXC {str(e)[:100]}")
for mid in (sys.argv[1:] or ["18139426585637353"]):
    print("reel", mid)
    for v in ("v19.0", "v21.0", "v23.0", "v24.0"):
        b = f"https://graph.facebook.com/{v}"
        show(f"{v} edge", f"{b}/{mid}/comments", {"fields": "id,username,timestamp", "limit": 50, "access_token": tok})
    b = m.G
    show("edge no fields", f"{b}/{mid}/comments", {"access_token": tok})
    show("edge with text+replies", f"{b}/{mid}/comments", {"fields": "id,text,username,replies{username}", "limit": 50, "access_token": tok})
    show("edge limit 5", f"{b}/{mid}/comments", {"fields": "id,username", "limit": 5, "access_token": tok})
    show("field expansion", f"{b}/{mid}", {"fields": "comments_count,comments.limit(50){id,username,timestamp}", "access_token": tok})
    show("via user media", f"{b}/{mid}", {"fields": "comments_count,comments{id,username,hidden,like_count}", "access_token": tok})
    show("graph.instagram.com", f"https://graph.instagram.com/{mid}/comments", {"fields": "id,username", "access_token": tok2})
    try:
        j = requests.get(f"{b}/{mid}", params={"fields": "media_product_type,is_comment_enabled,permalink,owner,shortcode,timestamp", "access_token": tok}, timeout=30).json()
        print("  media:", {k: j.get(k) for k in ("media_product_type", "is_comment_enabled", "timestamp", "permalink")})
    except Exception as e:
        print("  media EXC", e)
