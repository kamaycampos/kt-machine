"""READ-ONLY (4 Nov 2026): what tells a GIF-only comment from a comment whose words Instagram
withheld? Both came back with no text. Prints field PRESENCE and values, never usernames."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
os.environ["DM_BRAND"] = "AR_"
import dm_reply as m
tok = m.env("FB_ACCESS_TOKEN")
CASES = {"GIF only (wrong DM)": "18111593861614618", "Debra RISE (withheld)": "18069268760785345",
         "test RISE (normal)": "18091163465303677"}
FIELDS = ["text", "timestamp", "like_count", "hidden", "parent_id", "legacy_instagram_comment_id",
          "media{id,media_type}", "user", "attachment", "attachments", "media_type", "media_url",
          "gif", "sticker", "is_gif", "comment_type", "reactions", "message", "has_media"]
for name, cid in CASES.items():
    print(f"== {name} ...{cid[-5:]}")
    for f in FIELDS:
        try:
            j = m._get(f"{m.G}/{cid}", {"fields": f, "access_token": tok}); j.pop("id", None)
            print(f"   {f}: {json.dumps(j)[:160] if j else 'ABSENT'}")
        except Exception as e:
            print(f"   {f}: ERR {str(e)[:90]}")
    try:
        r = m._get(f"{m.G}/{cid}", {"access_token": tok}); r.pop("id", None)
        print(f"   (default fields): {sorted(r)}")
    except Exception as e:
        print(f"   (default): ERR {str(e)[:90]}")
# and how each looks inside the comment LIST the bot reads
for name, cid in CASES.items():
    pass
media = m._get(f"{m.G}/{m.env('IG_USER_ID')}/media", {"fields": "id", "limit": 25, "access_token": tok}).get("data", [])
want = set(CASES.values())
for p in media:
    for c in m._get(f"{m.G}/{p['id']}/comments", {"fields": "id,text,timestamp,like_count,hidden,legacy_instagram_comment_id",
                                                   "limit": 50, "access_token": tok}).get("data", []):
        if c["id"] in want:
            c2 = dict(c); c2.pop("id")
            print(f"LIST ...{c['id'][-5:]}: keys={sorted(c2)} text={c.get('text')!r} legacy={c.get('legacy_instagram_comment_id')}")
        elif not (c.get("text") or "").strip():
            print(f"LIST other blank ...{c['id'][-5:]} at {c['timestamp'][:16]}: keys={sorted(c)} text={c.get('text')!r}")
