#!/usr/bin/env python3
"""READ-ONLY (7 Nov 2026): did the Facebook DMs the bot "sent" really land in Messenger?

For every Facebook send in state/dms_ar.json it reads the message back by its id, and
the conversation it sits in, and prints only yes/no and counts - never a person's name
or words. Also prints each reel's caption, so we can see what the commenter was asked.
Sends nothing.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dm_reply as dm

page, tok = dm.env("FB_PAGE_ID"), dm.env("FB_ACCESS_TOKEN")
d = json.load(open(dm.STATE))
fb = {cid: r for cid, r in d["sent"].items() if r.get("platform") == "facebook"}
print(f"facebook sends on record: {len(fb)}")

for cid, r in fb.items():
    tag = cid[-6:]
    print(f"\n[{tag}] keyword {r['keyword']}, comment {r['comment_at'][:16]}, sent {r['sent_at'][:16]}")
    try:
        cap = dm._get(f"{dm.G}/{r['post']}", {"fields": "description", "access_token": tok}).get("description") or ""
        print(f"  reel caption first line: {cap.splitlines()[0][:90] if cap else '(none)'}")
        print(f"  caption asks for a comment: {'comment' in cap.lower()}")
    except Exception as e:
        print("  reel ERR", str(e)[:140])
    try:
        m = dm._get(f"{dm.G}/{r['message']}", {"fields": "created_time,from,to,message", "access_token": tok})
        frm = (m.get("from") or {}).get("id")
        to = [x.get("id") for x in (m.get("to") or {}).get("data", [])]
        print(f"  message exists: True, created {m.get('created_time', '')[:16]}, from the Page: {frm == page},"
              f" to someone else: {bool(to) and page not in to}, carries the link: {'http' in (m.get('message') or '')}")
    except Exception as e:
        print("  message ERR", str(e)[:160])

# The conversations the bot opened: did the person read it or write back?
try:
    convs = dm._get(f"{dm.G}/{page}/conversations", {
        "fields": "updated_time,message_count,unread_count,messages.limit(5){id,from,created_time}",
        "limit": 25, "access_token": tok}).get("data", [])
    sent_ids = {r["message"] for r in fb.values()}
    print(f"\nPage Messenger conversations readable: {len(convs)}")
    for c in convs:
        msgs = (c.get("messages") or {}).get("data", [])
        if not any(x.get("id") in sent_ids for x in msgs):
            continue
        theirs = sum(1 for x in msgs if (x.get("from") or {}).get("id") != page)
        print(f"  conversation updated {c.get('updated_time', '')[:16]}: {c.get('message_count')} messages,"
              f" {theirs} from the person, holds a bot DM: True")
except Exception as e:
    print("conversations ERR", str(e)[:160])
