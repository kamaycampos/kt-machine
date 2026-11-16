#!/usr/bin/env python3
"""READ-ONLY (16 Nov 2026): "X got the message but no reply under their comment" - who sent it?

Lists the Instagram conversations of the last WHO_DAYS days as the AR key sees them. For each
message from the account: when, whether it carries a link, and whether it is one the bot has on
record (state/dms_ar.json). A link message the bot has no record of was sent by a person or by
another tool - and nothing but the bot writes the public reply. People are named only by the
sha256 of their lowercase username (WHO_SHA, comma-separated); no names or words are printed.
Sends nothing."""
import hashlib, json, os, sys
from datetime import datetime, timedelta, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DM_BRAND", "AR_")
import dm_reply as m

WHOS = {w.strip() for w in (os.environ.get("WHO_SHA") or "").lower().split(",") if w.strip()}
DAYS = int(os.environ.get("WHO_DAYS") or 0) or 7
page, ig, tok = m.env("FB_PAGE_ID"), m.env("IG_USER_ID"), m.env("FB_ACCESS_TOKEN")
d = json.load(open(m.STATE))
bot = {r.get("message"): cid for cid, r in d["sent"].items() if r.get("platform") == "instagram"}
bot_times = sorted(r["sent_at"][:16] for r in d["sent"].values() if r.get("platform") == "instagram")
cut = (datetime.now(timezone.utc) - timedelta(days=DAYS)).strftime("%Y-%m-%dT%H:%M")
mine = m._get(f"{m.G}/{ig}", {"fields": "username", "access_token": tok}).get("username", "")
print(f"bot's Instagram sends on record: {len(bot)} at {bot_times}")
url, params, n, links, unrec = f"{m.G}/{page}/conversations", {
    "platform": "instagram", "limit": 25, "access_token": tok,
    "fields": "updated_time,participants,messages.limit(12){id,from,created_time,message}"}, 0, 0, 0
pages = 0
while url and pages < 6:
    try:
        j = m._get(url, params)
    except Exception as e:
        print("conversations ERR", str(e)[:200]); break
    pages += 1
    stop = False
    for c in j.get("data", []):
        if c.get("updated_time", "")[:16] < cut:
            stop = True; continue
        n += 1
        names = [p.get("username", "") for p in (c.get("participants") or {}).get("data", []) if p.get("username") != mine]
        who = "TARGET" if any(hashlib.sha256(x.lower().encode()).hexdigest() in WHOS for x in names) else "other"
        print(f"conversation updated {c['updated_time'][:16]} [{who}]")
        for x in reversed((c.get("messages") or {}).get("data", [])):
            ours = (x.get("from") or {}).get("username") == mine
            link = "http" in (x.get("message") or "")
            onrec = x.get("id") in bot or (ours and link and any(abs((datetime.fromisoformat(x["created_time"][:16]) - datetime.fromisoformat(t)).total_seconds()) <= 120 for t in bot_times))
            links += ours and link
            unrec += ours and link and not onrec
            print(f"    {x.get('created_time', '')[:16]} {'FROM US' if ours else 'from them'} link={link} chars={len(x.get('message') or '')}"
                  + (f" bot_record={'YES' if onrec else 'NO - not sent by the bot'}" if ours and link else ""))
    url, params = (None if stop else (j.get("paging") or {}).get("next")), {}
print(f"conversations in the last {DAYS} days: {n} | link messages from the account: {links} | of those NOT on the bot's record: {unrec}")
